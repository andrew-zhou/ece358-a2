#include <stdio.h>
#include <stdlib.h>
#include <string.h>

char *buildCommand(char *script, char **commandLineArguments, int commandLineArgumentsSize) {
    unsigned long commandLength = 0;

    commandLength += strlen("python3 ");
    commandLength += strlen(script);
    
    for (int i = 1; i < commandLineArgumentsSize; i++) {
        commandLength += 3; // For the preceding space
        commandLength += strlen(commandLineArguments[i]);
    }

    char* command = (char*) malloc(commandLength + 1);
    command[0] = '\0';

    strcat(command, "python3 ");
    strcat(command, script);
    for (int i = 1; i < commandLineArgumentsSize; i++) {
        strcat(command, " "); // For the preceding space
        strcat(command, "'");
        strcat(command, commandLineArguments[i]);
        strcat(command, "'");
    }

    return command;
}

int main(int argc, char *argv[]) {
    char *command = buildCommand("src/server.py", argv, argc);
    system(command);
    free(command);
    return 0;
}
