vpath %.c ./src
CC = gcc
CFLAGS = -std=c99
MAKEFILE_NAME = ${firstword ${MAKEFILE_LIST}}

OBJECT = pa2-358s17.o
EXEC = pa2-358s17

# substitute ".o" with ".d"
DEPENDS = ${OBJECT:.o=.d}

.PHONY : all clean

# build all executables
all : ${EXEC}

# OPTIONAL : changes to this file => recompile
${OBJECT} : ${MAKEFILE_NAME}

# include *.d files containing program dependences
-include ${DEPENDS}

# remove files that can be regenerated
clean :
	rm -f *.d *.o ${EXEC}
