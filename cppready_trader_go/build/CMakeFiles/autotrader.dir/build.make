# CMAKE generated file: DO NOT EDIT!
# Generated by "Unix Makefiles" Generator, CMake Version 3.26

# Delete rule output on recipe failure.
.DELETE_ON_ERROR:

#=============================================================================
# Special targets provided by cmake.

# Disable implicit rules so canonical targets will work.
.SUFFIXES:

# Disable VCS-based implicit rules.
% : %,v

# Disable VCS-based implicit rules.
% : RCS/%

# Disable VCS-based implicit rules.
% : RCS/%,v

# Disable VCS-based implicit rules.
% : SCCS/s.%

# Disable VCS-based implicit rules.
% : s.%

.SUFFIXES: .hpux_make_needs_suffix_list

# Command-line flag to silence nested $(MAKE).
$(VERBOSE)MAKESILENT = -s

#Suppress display of executed commands.
$(VERBOSE).SILENT:

# A target that is always out of date.
cmake_force:
.PHONY : cmake_force

#=============================================================================
# Set environment variables for the build.

# The shell in which to execute make rules.
SHELL = /bin/sh

# The CMake executable.
CMAKE_COMMAND = /usr/local/Cellar/cmake/3.26.0/bin/cmake

# The command to remove a file.
RM = /usr/local/Cellar/cmake/3.26.0/bin/cmake -E rm -f

# Escaping for special characters.
EQUALS = =

# The top-level source directory on which CMake was run.
CMAKE_SOURCE_DIR = /Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go

# The top-level build directory on which CMake was run.
CMAKE_BINARY_DIR = /Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go/build

# Include any dependencies generated for this target.
include CMakeFiles/autotrader.dir/depend.make
# Include any dependencies generated by the compiler for this target.
include CMakeFiles/autotrader.dir/compiler_depend.make

# Include the progress variables for this target.
include CMakeFiles/autotrader.dir/progress.make

# Include the compile flags for this target's objects.
include CMakeFiles/autotrader.dir/flags.make

CMakeFiles/autotrader.dir/main.cc.o: CMakeFiles/autotrader.dir/flags.make
CMakeFiles/autotrader.dir/main.cc.o: /Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go/main.cc
CMakeFiles/autotrader.dir/main.cc.o: CMakeFiles/autotrader.dir/compiler_depend.ts
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --progress-dir=/Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go/build/CMakeFiles --progress-num=$(CMAKE_PROGRESS_1) "Building CXX object CMakeFiles/autotrader.dir/main.cc.o"
	/Library/Developer/CommandLineTools/usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -MD -MT CMakeFiles/autotrader.dir/main.cc.o -MF CMakeFiles/autotrader.dir/main.cc.o.d -o CMakeFiles/autotrader.dir/main.cc.o -c /Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go/main.cc

CMakeFiles/autotrader.dir/main.cc.i: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Preprocessing CXX source to CMakeFiles/autotrader.dir/main.cc.i"
	/Library/Developer/CommandLineTools/usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -E /Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go/main.cc > CMakeFiles/autotrader.dir/main.cc.i

CMakeFiles/autotrader.dir/main.cc.s: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Compiling CXX source to assembly CMakeFiles/autotrader.dir/main.cc.s"
	/Library/Developer/CommandLineTools/usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -S /Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go/main.cc -o CMakeFiles/autotrader.dir/main.cc.s

CMakeFiles/autotrader.dir/autotrader.cc.o: CMakeFiles/autotrader.dir/flags.make
CMakeFiles/autotrader.dir/autotrader.cc.o: /Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go/autotrader.cc
CMakeFiles/autotrader.dir/autotrader.cc.o: CMakeFiles/autotrader.dir/compiler_depend.ts
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --progress-dir=/Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go/build/CMakeFiles --progress-num=$(CMAKE_PROGRESS_2) "Building CXX object CMakeFiles/autotrader.dir/autotrader.cc.o"
	/Library/Developer/CommandLineTools/usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -MD -MT CMakeFiles/autotrader.dir/autotrader.cc.o -MF CMakeFiles/autotrader.dir/autotrader.cc.o.d -o CMakeFiles/autotrader.dir/autotrader.cc.o -c /Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go/autotrader.cc

CMakeFiles/autotrader.dir/autotrader.cc.i: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Preprocessing CXX source to CMakeFiles/autotrader.dir/autotrader.cc.i"
	/Library/Developer/CommandLineTools/usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -E /Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go/autotrader.cc > CMakeFiles/autotrader.dir/autotrader.cc.i

CMakeFiles/autotrader.dir/autotrader.cc.s: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Compiling CXX source to assembly CMakeFiles/autotrader.dir/autotrader.cc.s"
	/Library/Developer/CommandLineTools/usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -S /Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go/autotrader.cc -o CMakeFiles/autotrader.dir/autotrader.cc.s

# Object files for target autotrader
autotrader_OBJECTS = \
"CMakeFiles/autotrader.dir/main.cc.o" \
"CMakeFiles/autotrader.dir/autotrader.cc.o"

# External object files for target autotrader
autotrader_EXTERNAL_OBJECTS =

autotrader: CMakeFiles/autotrader.dir/main.cc.o
autotrader: CMakeFiles/autotrader.dir/autotrader.cc.o
autotrader: CMakeFiles/autotrader.dir/build.make
autotrader: libs/ready_trader_go/libready_trader_go_lib.a
autotrader: /usr/local/lib/libboost_date_time-mt.dylib
autotrader: /usr/local/lib/libboost_log-mt.dylib
autotrader: /usr/local/lib/libboost_system-mt.dylib
autotrader: /usr/local/lib/libboost_thread-mt.dylib
autotrader: /usr/local/lib/libboost_container-mt.dylib
autotrader: /usr/local/lib/libboost_graph-mt.dylib
autotrader: /usr/local/lib/libboost_math_c99-mt.dylib
autotrader: /usr/local/lib/libboost_math_c99f-mt.dylib
autotrader: /usr/local/lib/libboost_math_tr1-mt.dylib
autotrader: /usr/local/lib/libboost_math_tr1f-mt.dylib
autotrader: /usr/local/lib/libboost_random-mt.dylib
autotrader: /usr/local/lib/libboost_regex-mt.dylib
autotrader: /usr/local/lib/libboost_timer-mt.dylib
autotrader: /usr/local/lib/libboost_unit_test_framework-mt.dylib
autotrader: /usr/local/lib/libboost_filesystem-mt.dylib
autotrader: /usr/local/lib/libboost_atomic-mt.dylib
autotrader: /usr/local/lib/libboost_chrono-mt.dylib
autotrader: CMakeFiles/autotrader.dir/link.txt
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --bold --progress-dir=/Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go/build/CMakeFiles --progress-num=$(CMAKE_PROGRESS_3) "Linking CXX executable autotrader"
	$(CMAKE_COMMAND) -E cmake_link_script CMakeFiles/autotrader.dir/link.txt --verbose=$(VERBOSE)

# Rule to build all files generated by this target.
CMakeFiles/autotrader.dir/build: autotrader
.PHONY : CMakeFiles/autotrader.dir/build

CMakeFiles/autotrader.dir/clean:
	$(CMAKE_COMMAND) -P CMakeFiles/autotrader.dir/cmake_clean.cmake
.PHONY : CMakeFiles/autotrader.dir/clean

CMakeFiles/autotrader.dir/depend:
	cd /Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go/build && $(CMAKE_COMMAND) -E cmake_depends "Unix Makefiles" /Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go /Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go /Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go/build /Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go/build /Users/maxwellbrown/Desktop/ReadyTraderGo/cppready_trader_go/build/CMakeFiles/autotrader.dir/DependInfo.cmake --color=$(COLOR)
.PHONY : CMakeFiles/autotrader.dir/depend
