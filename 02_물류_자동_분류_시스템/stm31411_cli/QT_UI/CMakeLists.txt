cmake_minimum_required(VERSION 3.19)
project(QT_UI LANGUAGES CXX)

find_package(Qt6 6.5 REQUIRED COMPONENTS Core Widgets SerialPort LinguistTools)

qt_standard_project_setup()

qt_add_executable(QT_UI
    WIN32 MACOSX_BUNDLE
    main.cpp
    mainwindow.cpp
    mainwindow.h
    mainwindow.ui
    packetparser.cpp
    packetparser.h
    serialworker.cpp
    serialworker.h
)

qt_add_translations(
    TARGETS QT_UI
    TS_FILES QT_UI_ko_KR.ts
)

target_link_libraries(QT_UI
    PRIVATE
        Qt6::Core
        Qt6::Widgets
        Qt6::SerialPort
)

install(TARGETS QT_UI
    BUNDLE  DESTINATION .
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
)

qt_generate_deploy_app_script(
    TARGET QT_UI
    OUTPUT_SCRIPT deploy_script
    NO_UNSUPPORTED_PLATFORM_ERROR
)
install(SCRIPT ${deploy_script})