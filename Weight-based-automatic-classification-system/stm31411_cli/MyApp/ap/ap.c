#include "ap.h"
#include <math.h>
#include "pca9685.h"
#include "pir.h"

/* 
 *  LoadCell Task
 *  */

#define LOADCELL_TASK_PERIOD_MS    250
#define TARE_SAMPLE_COUNT          20
#define HX711_READY_TIMEOUT_MS     500

#define DEFAULT_TARE_OFFSET        (-5757)
#define SCALE_FACTOR_DEFAULT       50.46f
#define DEADBAND_GRAM              2.0f
#define MEDIAN_SIZE                7
#define EMA_ALPHA_SLOW             0.1f
#define EMA_ALPHA_FAST             0.6f
#define EMA_CHANGE_THRESH_G        5.0f
#define STABLE_COUNT               5
#define STABLE_THRESH_G            2.0f
#define OBJECT_DETECT_G            25.0f
#define OBJECT_RELEASE_G           12.0f
#define ZERO_TRACK_LIMIT_G         15.0f
#define ZERO_TRACK_STABLE_G         1.0f
#define ZERO_TRACK_ALPHA            0.02f
#define ZERO_TRACK_RELEASE_WAIT_MS  3000

static volatile int32_t  g_tare_offset         = DEFAULT_TARE_OFFSET;
static volatile float    g_scale_factor        = SCALE_FACTOR_DEFAULT;
static volatile bool     g_tare_request        = false;
static volatile bool     g_loadcell_auto_print = false;
static volatile bool     g_invert              = true;

static int32_t g_med_buf[MEDIAN_SIZE] = {0};
static uint8_t g_med_idx  = 0;
static bool    g_med_full = false;

static int32_t medianFilter(int32_t new_raw)
{
    g_med_buf[g_med_idx] = new_raw;
    g_med_idx = (g_med_idx + 1) % MEDIAN_SIZE;
    if (g_med_idx == 0) g_med_full = true;

    uint8_t count = g_med_full ? MEDIAN_SIZE : g_med_idx;
    int32_t sorted[MEDIAN_SIZE];
    for (uint8_t i = 0; i < count; i++) sorted[i] = g_med_buf[i];

    for (uint8_t i = 0; i < count - 1; i++)
        for (uint8_t j = 0; j < count - i - 1; j++)
            if (sorted[j] > sorted[j+1])
            {
                int32_t tmp  = sorted[j];
                sorted[j]    = sorted[j+1];
                sorted[j+1]  = tmp;
            }

    return sorted[count / 2];
}

static float g_ema_value       = 0.0f;
static bool  g_ema_initialized = false;

static float adaptiveEma(int32_t new_raw)
{
    if (!g_ema_initialized)
    {
        g_ema_value       = (float)new_raw;
        g_ema_initialized = true;
        return g_ema_value;
    }

    float diff_g = ((float)new_raw - g_ema_value) / g_scale_factor;
    if (g_invert) diff_g = -diff_g;

    float alpha = ((diff_g > EMA_CHANGE_THRESH_G) || (diff_g < -EMA_CHANGE_THRESH_G))
                  ? EMA_ALPHA_FAST : EMA_ALPHA_SLOW;

    g_ema_value = alpha * (float)new_raw + (1.0f - alpha) * g_ema_value;
    return g_ema_value;
}

volatile float   g_stable_last   = 0.0f;
volatile uint8_t g_stable_count  = 0;
volatile float   g_stable_weight = 0.0f;

static void updateStable(float weight)
{
    float diff     = weight - g_stable_last;
    float abs_diff = diff < 0.0f ? -diff : diff;

    if (abs_diff <= STABLE_THRESH_G)
    {
        if (diff > 1.0f)
        {
            g_stable_count = 0;
        }
        else
        {
            g_stable_count++;
            if (g_stable_count >= STABLE_COUNT)
            {
                g_stable_weight = weight;
                g_stable_count  = STABLE_COUNT;
            }
        }
    }
    else
    {
        g_stable_count  = 0;
        g_stable_weight = weight;
    }
    g_stable_last = weight;
}

static void resetFilters(int32_t tare_val)
{
    for (uint8_t i = 0; i < MEDIAN_SIZE; i++) g_med_buf[i] = tare_val;
    g_med_idx  = 0;
    g_med_full = true;

    g_ema_value       = (float)tare_val;
    g_ema_initialized = true;

    g_stable_last   = 0.0f;
    g_stable_count  = 0;
    g_stable_weight = 0.0f;
}

static float calcWeight(int32_t raw)
{
    int32_t median   = medianFilter(raw);
    float   filtered = adaptiveEma(median);
    int32_t net      = (int32_t)filtered - g_tare_offset;
    if (g_invert) net = -net;
    float   weight   = (float)net / g_scale_factor;
    if (weight < DEADBAND_GRAM) weight = 0.0f;
    return weight;
}

static bool readRaw(int32_t *out)
{
    uint32_t timeout = HX711_READY_TIMEOUT_MS;
    while (!hx711IsReady() && timeout > 0)
    {
        osDelay(1);
        timeout--;
    }
    if (timeout == 0) return false;
    *out = hx711Read();
    return true;
}

static void runTare(void)
{
    int32_t sum = 0;
    int32_t raw;

    cliPrintf("Tare start... (%d samples)\r\n", TARE_SAMPLE_COUNT);

    for (uint8_t i = 0; i < TARE_SAMPLE_COUNT; i++)
    {
        if (!readRaw(&raw))
        {
            cliPrintf("HX711 no response (Tare aborted)\r\n");
            return;
        }
        sum += raw;
        osDelay(10);
    }

    g_tare_offset = sum / TARE_SAMPLE_COUNT;
    resetFilters(g_tare_offset);
    cliPrintf("Tare done. offset = %ld\r\n", (long)g_tare_offset);
}

void cliLoadCell(uint8_t argc, char **argv)
{
    if (argc < 2)
    {
        cliPrintf("Usage: loadcell tare\r\n");
        cliPrintf("       loadcell rawtare\r\n");
        cliPrintf("       loadcell read\r\n");
        cliPrintf("       loadcell auto [on|off]\r\n");
        cliPrintf("       loadcell scale [value]\r\n");
        cliPrintf("       loadcell invert\r\n");
        return;
    }

    if (strcmp(argv[1], "tare") == 0)
    {
        g_tare_request = true;
        cliPrintf("Tare requested.\r\n");
    }
    else if (strcmp(argv[1], "rawtare") == 0)
    {
        int32_t sum = 0;
        int32_t raw;
        for (uint8_t i = 0; i < 20; i++)
        {
            if (readRaw(&raw)) sum += raw;
            osDelay(10);
        }
        cliPrintf("Current raw avg: %ld\r\n", (long)(sum / 20));
        cliPrintf("-> Replace DEFAULT_TARE_OFFSET in ap.c with this value.\r\n");
    }
    else if (strcmp(argv[1], "read") == 0)
    {
        int32_t raw;
        if (!readRaw(&raw)) { cliPrintf("HX711 no response\r\n"); return; }
        cliPrintf("raw=%ld  weight=%.2f g\r\n", (long)raw, calcWeight(raw));
    }
    else if (strcmp(argv[1], "auto") == 0 && argc == 3)
    {
        if (strcmp(argv[2], "on") == 0)
        {
            g_loadcell_auto_print = true;
            cliPrintf("LoadCell auto print ON\r\n");
        }
        else if (strcmp(argv[2], "off") == 0)
        {
            g_loadcell_auto_print = false;
            cliPrintf("LoadCell auto print OFF\r\n");
        }
        else { cliPrintf("Usage: loadcell auto [on|off]\r\n"); }
    }
    else if (strcmp(argv[1], "invert") == 0)
    {
        g_invert = !g_invert;
        cliPrintf("Sign invert %s\r\n", g_invert ? "ON" : "OFF");
    }
    else if (strcmp(argv[1], "scale") == 0 && argc == 3)
    {
        float val = strtof(argv[2], NULL);
        if (val > 0.0f) { g_scale_factor = val; cliPrintf("Scale factor = %.2f\r\n", g_scale_factor); }
        else              cliPrintf("Invalid scale factor\r\n");
    }
    else { cliPrintf("Unknown command\r\n"); }
}

#define CLASSIFY_HEAVY_G           60.0f
#define CONVEYOR_RUN_MS            3000

typedef enum {
    STATE_WAIT_OBJECT,
    STATE_MEASURING,
    STATE_ARM_MOVING,
    STATE_CONVEYOR_RUNNING,
    STATE_DONE,
    STATE_IDLE,
    STATE_INIT,
} SystemState_t;

static volatile SystemState_t g_system_state   = STATE_IDLE;
volatile bool          g_system_enabled = false;

osSemaphoreId_t g_arm_done_sem = NULL;

volatile bool arm_running      = false;
volatile bool arm_init_running = false;

volatile bool  g_object_present = false;

void loadCellSystemTask(void *argument)
{
    int32_t  raw             = 0;
    uint32_t release_time_ms = 0;
    float    prev_weight_g   = 0.0f;

    hx711Init(HX711_GAIN_128);
    LOG_INF("HX711 Init OK");

    osDelay(500);
    runTare();

    for (;;)
    {
        if (g_tare_request)
        {
            g_tare_request   = false;
            runTare();
            g_object_present = false;
            release_time_ms  = 0;
            prev_weight_g    = 0.0f;
        }

        if (!readRaw(&raw))
        {
            LOG_WRN("HX711 timeout");
            osDelay(LOADCELL_TASK_PERIOD_MS);
            continue;
        }

        float weight = calcWeight(raw);
        updateStable(weight);

        if (!g_object_present)
        {
            if (g_stable_weight >= OBJECT_DETECT_G)
            {
                g_object_present = true;
                release_time_ms  = 0;
                cliPrintf("[LC] Object detected: %.2f g\r\n", g_stable_weight);
            }
        }
        else
        {
            if (g_stable_weight <= OBJECT_RELEASE_G)
            {
                g_object_present = false;
                release_time_ms  = osKernelGetTickCount();
                cliPrintf("[LC] Object removed\r\n");
            }
        }

        if (!g_object_present && release_time_ms != 0)
        {
            uint32_t elapsed = osKernelGetTickCount() - release_time_ms;

            if (elapsed >= ZERO_TRACK_RELEASE_WAIT_MS &&
                fabsf(g_stable_weight)                 < ZERO_TRACK_LIMIT_G &&
                fabsf(g_stable_weight - prev_weight_g) < ZERO_TRACK_STABLE_G)
            {
                int32_t filtered_raw = (int32_t)g_ema_value;
                g_tare_offset = (int32_t)(
                    (1.0f - ZERO_TRACK_ALPHA) * (float)g_tare_offset +
                    ZERO_TRACK_ALPHA          * (float)filtered_raw
                );
            }
        }

        if (g_loadcell_auto_print || g_system_enabled)
            cliPrintf("[LoadCell] raw=%ld  weight=%.2f g\r\n",
                      (long)raw, g_stable_weight);

        if (isMonitoringOn()) {
            float w = g_stable_weight;
            monitorUpdateValue(ID_ENV_HUMI, TYPE_FLOAT, &w);
        }

        prev_weight_g = g_stable_weight;
        osDelay(LOADCELL_TASK_PERIOD_MS);
    }
}

void robotArmTask(void) {

    pca9685SetAngleSmoothDual(0, 0, 1, 0, 1500);
    if (!arm_running) return;

    pca9685SetAngleSmooth(2, 90 , 1500);
    if (!arm_running) return;

    pca9685SetAngleSmooth(3, 45, 1500);
    if (!arm_running) return;

    pca9685SetAngleSmooth(4, 50, 1500);
    if (!arm_running) return;

    pca9685SetAngleSmoothDual(0, 120, 1, 120, 1500);
    if (!arm_running) return;

    pca9685SetAngleSmoothDual(3, 180, 4, 180, 1500);
    if (!arm_running) return;

    pca9685SetAngleSmooth(5, 90, 1500);
    if (!arm_running) return;

    pca9685SetAngleSmoothDual(3, 145, 4, 145, 1500);
    if (!arm_running) return;

    pca9685SetAngleSmoothDual(0, 0, 1, 0, 1500);

    pca9685SetAngleSmooth(4, 180, 1500);
    if (!arm_running) return;

    pca9685SetAngleSmooth(5, 5, 1500);
}

static void robotArmInitTask(void)
{
    pca9685SetAngleSmoothDual(0, 0, 1, 0, 1500);
    if (!arm_init_running) return;
    pca9685SetAngleSmooth(2, 90, 1500);
    if (!arm_init_running) return;
    pca9685SetAngleSmooth(4, 180, 1500);
    if (!arm_init_running) return;
    pca9685SetAngleSmooth(5, 5, 1500);
}

void systemTask(void *argument)
{
    float    measured_weight   = 0.0f;
    uint32_t conveyor_start_ms = 0;
    bool     init_sequence     = false;

    osDelay(1000);

    g_system_state = STATE_IDLE;
    cliPrintf("[SYS] systemTask started - type 'system on' to begin\r\n");

    for (;;)
    {
        if (!g_system_enabled)
        {
            g_system_state = STATE_IDLE;
            osDelay(100);
            continue;
        }

        switch (g_system_state)
        {
            case STATE_IDLE:
                g_system_state = STATE_INIT;
                cliPrintf("[SYS] -> INIT\r\n");
                break;

            case STATE_INIT:
                init_sequence    = true;
                arm_init_running = true;
                g_system_state   = STATE_ARM_MOVING;
                cliPrintf("[SYS] Init sequence start\r\n");
                break;

            case STATE_WAIT_OBJECT:
                if (g_object_present)
                {
                    g_stable_count = 0;
                    cliPrintf("[SYS] -> MEASURING\r\n");
                    g_system_state = STATE_MEASURING;
                }
                break;

            case STATE_MEASURING:
                if (!g_object_present)
                {
                    cliPrintf("[SYS] Object removed during measurement -> WAIT\r\n");
                    g_system_state = STATE_WAIT_OBJECT;
                    break;
                }
                if (g_stable_count >= STABLE_COUNT)
                {
                    measured_weight = g_stable_weight;

                    if (measured_weight >= CLASSIFY_HEAVY_G)
                    {
                        Flag_SetLeft();
                        cliPrintf("[SYS] Heavy object %.2f g -> FLAG LEFT\r\n", measured_weight);
                    }
                    else
                    {
                        Flag_SetRight();
                        cliPrintf("[SYS] Light object %.2f g -> FLAG RIGHT\r\n", measured_weight);
                    }

                    arm_running    = true;
                    g_system_state = STATE_ARM_MOVING;
                    cliPrintf("[SYS] -> ARM_MOVING\r\n");
                }
                break;

            case STATE_ARM_MOVING:
                osSemaphoreAcquire(g_arm_done_sem, osWaitForever);
                if (init_sequence)
                {
                    init_sequence  = false;
                    g_system_state = STATE_WAIT_OBJECT;
                    cliPrintf("[SYS] Init done -> WAIT_OBJECT\r\n");
                }
                else
                {
                    Conveyor_Start(CONVEYOR_SLOW, CONVEYOR_DIR_BACKWARD);
                    conveyor_start_ms = osKernelGetTickCount();
                    g_system_state    = STATE_CONVEYOR_RUNNING;
                    cliPrintf("[SYS] Arm done -> CONVEYOR_RUNNING\r\n");
                }
                break;

            case STATE_CONVEYOR_RUNNING:
            {
                uint32_t elapsed = osKernelGetTickCount() - conveyor_start_ms;
                if (elapsed >= CONVEYOR_RUN_MS)
                {
                    Conveyor_Stop();
                    Flag_SetCenter();
                    g_system_state = STATE_DONE;
                    cliPrintf("[SYS] Conveyor stop -> DONE\r\n");
                }
                break;
            }

            case STATE_DONE:
                measured_weight   = 0.0f;
                conveyor_start_ms = 0;
                g_system_state    = STATE_WAIT_OBJECT;
                cliPrintf("[SYS] -> WAIT_OBJECT\r\n");
                break;

            default:
                g_system_state = STATE_WAIT_OBJECT;
                break;
        }

        osDelay(50);
    }
}

void cliArm(uint8_t argc, char **argv) {
    if (argc == 2) {
        if (strcmp(argv[1], "start") == 0) {
            arm_running = true;
            cliPrintf("Arm Started\r\n");
        } else if (strcmp(argv[1], "stop") == 0) {
            arm_running = false;
            cliPrintf("Arm Stopped\r\n");
        } else {
            cliPrintf("Usage: arm [start/stop]\r\n");
        }
    } else {
        cliPrintf("Usage: arm [start/stop]\r\n");
    }
}

void cliButton(uint8_t argc, char **argv)
{
  if (argc == 2)
  {
    if (strcmp(argv[1], "on") == 0)
    {
      buttonEnable(true);
      cliPrintf("Button Interrupt Report: ON\r\n");
    }
    else if (strcmp(argv[1], "off") == 0)
    {
      buttonEnable(false);
      cliPrintf("Button Interrupt Report: OFF\r\n");
    }
  }
  else
  {
    cliPrintf("Usage: button [on/off]\r\n");
    cliPrintf("Current Status: %s\r\n", buttonGetEnable() ? "ON" : "OFF");
  }
}

static bool isSafeAddress(uint32_t addr)
{
  if (0x08000000 <= addr && addr <= 0x0807FFFF) return true;
  if (0x20000000 <= addr && addr <= 0x20001FFF) return true;
  if (0x1FFF0000 <= addr && addr <= 0x1FFF7A1F) return true;
  if (0x40000000 <= addr && addr <= 0x5FFFFFFF) return true;
  return false;
}

void cliMd(uint8_t argc, char **argv)
{
  if (argc >= 2)
  {
    uint32_t addr = strtoul(argv[1], NULL, 16);
    uint32_t length = 16;
    if (argc >= 3) length = strtoul(argv[2], NULL, 0);

    for (uint32_t i = 0; i < length; i += 16)
    {
      cliPrintf("0x%08x : ", addr + i);
      for (uint32_t j = 0; j < 16; j++)
      {
        if (i + j < length)
        {
          uint32_t target_addr = (addr + i + j);
          if (isSafeAddress(target_addr))
          {
            uint8_t val = *((volatile uint8_t *)target_addr);
            cliPrintf("%02X ", val);
          }
          else { cliPrintf("Not valid address!!\r\n"); break; }
        }
        else { cliPrintf("   "); }
      }
      cliPrintf(" | ");
      for (uint32_t j = 0; j < 16; j++)
      {
        if (i + j < length)
        {
          uint32_t target_addr = (addr + i + j);
          if (isSafeAddress(target_addr))
          {
            uint8_t val = *((volatile uint8_t *)target_addr);
            if (val >= 0x20 && val <= 0x7E) cliPrintf("%c", val);
            else                             cliPrintf(".");
          }
          else { cliPrintf("Not valid address!!\r\n"); break; }
        }
      }
      cliPrintf("\r\n");
    }
  }
  else
  {
    cliPrintf("Usage : md [add(hex)] [length]\r\n");
    cliPrintf("        md 08000000 32\r\n");
  }
}

void cliGpio(uint8_t argc, char **argv)
{
  if (argc >= 3)
  {
    char port_char = tolower(argv[2][0]);
    int pin_num = atoi(&argv[2][1]);
    uint8_t port_idx = port_char - 'a';

    if (strcmp(argv[1], "read") == 0)
    {
      int8_t state = gpioExtRead(port_idx, pin_num);
      if (state < 0) cliPrintf("Invalid Port or Pin (ex:a5, b12)\r\n");
      else           cliPrintf("GPIO %c%d=%d\r\n", toupper(port_char), pin_num, state);
    }
    else if (strcmp(argv[1], "write") == 0 && argc == 4)
    {
      int val = atoi(argv[3]);
      if (gpioExtWrite(port_idx, pin_num, val) == true)
        cliPrintf("GPIO %c%d Set to %d\r\n", toupper(port_char), pin_num, val);
      else
        cliPrintf("Invalid Port or Pin (ex:a5, b12)\r\n");
    }
    else
    {
      cliPrintf("Usage: gpio read [a~h][0~15]\r\n");
      cliPrintf("       gpio write [a~h][0~15] [0|1]\r\n");
    }
  }
  else
  {
    cliPrintf("Usage: gpio read [a~h][0~15]\r\n");
    cliPrintf("       gpio write [a~h][0~15] [0|1]\r\n");
  }
}

static uint32_t led_toggle_period = 0;
void cliLed(uint8_t argc, char **argv)
{
  if (argc >= 2)
  {
    if (strcmp(argv[1], "on") == 0)
    {
      led_toggle_period=0;
      ledOn();
      LOG_INF("LED ON");
    }
    else if (strcmp(argv[1], "off") == 0)
    {
      led_toggle_period=0;
      ledOff();
      LOG_INF("LED OFF");
    }
    else if (strcmp(argv[1], "toggle") == 0)
    {
      if(argc==3){
        led_toggle_period=atoi(argv[2]);
        if(led_toggle_period>0) LOG_INF("LED Auto-Toggled!!");
        else                    cliPrintf("Invalid Period\r\n");
      }
      else{
        led_toggle_period=0;
        ledToggle();
        LOG_INF("LED TOGGLE");
      }
    }
    else { cliPrintf("Invalid Command\r\n"); }
  }
  else
  {
    cliPrintf("Usage: led [on|off]\r\n");
    cliPrintf("     : led toggle\r\n");
    cliPrintf("     : led toggle [period]\r\n");
  }
}

void cliInfo(uint8_t argc, char **argv)
{
  if (argc == 1)
  {
    cliPrintf("===============================\r\n");
    cliPrintf("  HW Model   :  STM32F411\r\n");
    cliPrintf("  FW Version : V1.0.0\r\n");
    cliPrintf("  Build Date : %s %s\r\n", __DATE__, __TIME__);
    uint32_t uid0 = HAL_GetUIDw0();
    uint32_t uid1 = HAL_GetUIDw1();
    uint32_t uid2 = HAL_GetUIDw2();
    uint32_t dev  = HAL_GetDEVID();
    cliPrintf("  Serial Num : %08x-%08x-%08x\r\n", uid0, uid1, uid2);
    cliPrintf("  DeviceID   : %08x\r\n", dev);
    cliPrintf("===============================\r\n");
  }
  else if (argc == 2 || strcmp(argv[1], "uptime") == 0)
  {
    cliPrintf("System Uptime: %d ms\r\n", millis());
  }
  else
  {
    cliPrintf("Usage: info\r\n");
    cliPrintf("       info [uptime]\r\n");
  }
}

void cliSys(uint8_t argc, char **argv)
{
  if ((argc == 2) && strcmp(argv[1], "reset") == 0)
    NVIC_SystemReset();
  else
    cliPrintf("Usage: sys [reset]\r\n");
}

static uint32_t temp_read_period = 0;
void cliTemp(uint8_t argc, char **argv){
  if(argc==1)
  {
    if(temp_read_period >0) tempStopAuto();
    temp_read_period=0;
    float t=tempReadSingle();
    cliPrintf("Current Temp: %.2f *C\r\n", t);
  }
  else if(argc==2){
    int period =atoi(argv[1]);
    if(period>0){
      tempStartAuto();
      temp_read_period=period;
      cliPrintf("Temperature Auto-Read Started (%d ms)\r\n",period);
    }
    else{
      tempStopAuto();
      cliPrintf("Invalid Period\r\n");
    }
  }
  else{
    tempStopAuto();
    cliPrintf("Usage: temp\r\n");
    cliPrintf("       temp [period]\r\n");
  }
}

void StartDefaultTask(void *argument)
{
  apInit();
  for(;;) { apMain(); }
}

void cliConveyor(uint8_t argc, char **argv)
{
    if (argc < 2)
    {
        cliPrintf("Usage: conv start\r\n");
        cliPrintf("       conv stop\r\n");
        return;
    }

    if (strcmp(argv[1], "start") == 0)
    {
        Conveyor_Start(CONVEYOR_SLOW, CONVEYOR_DIR_BACKWARD);
        cliPrintf("Conveyor: START\r\n");
    }
    else if (strcmp(argv[1], "stop") == 0)
    {
        Conveyor_Stop();
        cliPrintf("Conveyor: STOP\r\n");
    }
    else
    {
        cliPrintf("Usage: conv [start|stop]\r\n");
    }
}

void ledSystemTask(void *argument)
{
  while (1)
  {
    if(led_toggle_period > 0){
      ledToggle();
      bool led_state=ledGetStatus();
      if(isMonitoringOn()) monitorUpdateValue(ID_OUT_LED_STATE,TYPE_BOOL,&led_state);
      else                 LOG_DBG("LED Toggle!");
      osDelay(led_toggle_period);
    }
    else{
      bool led_state=ledGetStatus();
      if(isMonitoringOn()) monitorUpdateValue(ID_OUT_LED_STATE,TYPE_BOOL,&led_state);
      osDelay(50);
    }
  }
}

void tempSystemTask(void *argument){
  while(1){
    if(temp_read_period>0){
      tempStartAuto();
      float t=tempReadAuto();
      if(isMonitoringOn()) monitorUpdateValue(ID_ENV_TEMP, TYPE_FLOAT, &t);
      else                 cliPrintf("Current Temp: %.2f *C\r\n", t);
      osDelay(temp_read_period);
    }
    else{ osDelay(50); }
  }
}

static uint32_t monitor_period = 0;
void monitorSystemTask(void *argument){
  while(1){
    if(isMonitoringOn()) monitorSendPacket();
    monitor_period=monitorGetPeriod();
    osDelay(monitor_period);
  }
}

void apStopAutoTask(void){
  monitorOff();
  led_toggle_period     = 0;
  temp_read_period      = 0;
  g_loadcell_auto_print = false;
  tempStopAuto();
  ledOff();
  Conveyor_Stop();
}

void apSyncPeriods(uint32_t period){
  if(period >0){
    tempStopAuto();
    temp_read_period=period;
    led_toggle_period=period;
    LOG_INF("Task Synchronized to %d ms", period);
  }
  else{
    temp_read_period=0;
    led_toggle_period=0;
  }
}

void armSystemTask(void *argument)
{
    LOG_INF("armSystemTask started!");
    while (1)
    {
        if (arm_init_running)
        {
            cliPrintf("[ARM] Init sequence start\r\n");
            robotArmInitTask();
            arm_init_running = false;

            if (g_arm_done_sem != NULL)
            {
                osSemaphoreRelease(g_arm_done_sem);
                cliPrintf("[ARM] Init done - semaphore released\r\n");
            }
        }
        else if (arm_running)
        {
            cliPrintf("[ARM] Sequence start\r\n");
            robotArmTask();
            arm_running = false;

            if (g_arm_done_sem != NULL)
            {
                osSemaphoreRelease(g_arm_done_sem);
                cliPrintf("[ARM] Sequence done - semaphore released\r\n");
            }
            else
            {
                cliPrintf("[ARM] WARNING: g_arm_done_sem is NULL\r\n");
            }
        }
        else
        {
            osDelay(50);
        }
    }
}

void cliSystem(uint8_t argc, char **argv)
{
    if (argc < 2)
    {
        cliPrintf("Usage: system on\r\n");
        cliPrintf("       system off\r\n");
        cliPrintf("       system status\r\n");
        return;
    }

    if (strcmp(argv[1], "on") == 0)
    {
        if (g_system_enabled)
        {
            cliPrintf("[SYS] Already running\r\n");
            return;
        }
        g_system_enabled = true;
        g_system_state   = STATE_IDLE;
        pirEnable(true);
        cliPrintf("[SYS] System ON (PIR auto-enabled)\r\n");
    }
    else if (strcmp(argv[1], "off") == 0)
    {
        g_system_enabled = false;
        arm_running      = false;
        Conveyor_Stop();
        Flag_SetCenter();
        cliPrintf("[SYS] System OFF - conveyor/arm stopped\r\n");
    }
    else if (strcmp(argv[1], "status") == 0)
    {
        const char *state_str[] = {
            "WAIT_OBJECT", "MEASURING", "ARM_MOVING",
            "CONVEYOR_RUNNING", "DONE", "IDLE", "INIT"
        };
        cliPrintf("[SYS] enabled=%s  state=%s\r\n",
                  g_system_enabled ? "ON" : "OFF",
                  state_str[g_system_state]);
    }
    else
    {
        cliPrintf("Usage: system [on|off|status]\r\n");
    }
}

void apInit()
{
  hwInit();
  LOG_INF("Application Init... Started");

  logInit();
  monitorInit();
  Conveyor_Init();

  g_arm_done_sem = osSemaphoreNew(1, 0, NULL);

  monitorSetSyncHandler(apSyncPeriods);
  cliSetCtrlHandler(apStopAutoTask);

  cliAdd("led",       cliLed);
  cliAdd("info",      cliInfo);
  cliAdd("sys",       cliSys);
  cliAdd("gpio",      cliGpio);
  cliAdd("md",        cliMd);
  cliAdd("button",    cliButton);
  cliAdd("temp",      cliTemp);
  cliAdd("arm",       cliArm);
  cliAdd("conv",      cliConveyor);
  cliAdd("loadcell",  cliLoadCell);
  cliAdd("flag",      cliFlag);
  cliAdd("pir",       cliPir);
  cliAdd("system",    cliSystem);

  if (pca9685Init() == true)
      LOG_INF("PCA9685 Init OK");
  else
      LOG_INF("PCA9685 Init FAIL");

  extern osThreadId_t myTaskArmHandle;
  if (myTaskArmHandle != NULL)
      LOG_INF("Arm task handle OK");
  else
      LOG_INF("Arm task handle NULL - creation FAILED");

  LOG_INF("systemTask - created in CubeMX freertos.c");
}

void apMain(void)
{
  uartPrintf(0, "LED Task Started!!\r\n");
  while (1)
  {
    cliMain();
    pirCheck();
    osDelay(1);
  }
}