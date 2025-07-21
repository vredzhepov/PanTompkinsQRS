#include <stdio.h>
#include "panTompkins.h"

int main(int argc, char *argv[])
{
    if (argc < 3)
    {
        fprintf(stderr, "Usage: PanTompkinsQRS infile outfile\n");
        return 1;
    }

    init(argv[1], argv[2]);
    panTompkins();

    return 0;
}
