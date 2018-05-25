#include <stdio.h>  
#include <unistd.h>  
#include <dirent.h>  
#include <stdlib.h>  
#include <sys/stat.h>  
#include <string.h>  
#include <assert.h>  
#include <libgen.h>  
  

void mkdirs(char *muldir)   
{  
    int i,len;  
    char str[512];      
    strncpy(str, muldir, 512);  
    len=strlen(str);  
    for( i=0; i<len; i++ )  
    {  
        if( str[i]=='/' )  
        {  
            str[i] = '\0';  
            if( access(str,0)!=0 )  
            {  
                mkdir( str, 0777 );  
            }  
            str[i]='/';  
        }  
    }  
    if( len>0 && access(str,0)!=0 )  
    {  
        mkdir( str, 0777 );  
    }  
    return;  
} 

void copy(char *filepath,char *savefile){
    FILE *fp1,*fp2 ;
    char c;
    if ((fp1=fopen(filepath, "r"))==NULL)
    {
        printf("connot open\n");
        exit(0);
    }

    if ((fp2=fopen(savefile, "a"))==NULL)
    {
        printf("connot open\n");
        exit(0);
    }

    while ((c = fgetc(fp1)) != EOF)
    {
        fputc(c,fp2);
    }
    fclose(fp1);
    fclose(fp2);
} 
  
  
int main(int argc, char **argv)  
{  
    printf("inputFile1:%s\n",argv[1]);
    printf("inputFile2:%s\n",argv[2]);
    printf("outputFile:%s\n",argv[3]);

    char output[50];
    strcpy(output,argv[3]);  
    mkdirs(dirname(argv[3]));

    copy(argv[1],output);
    copy(argv[2],output);
    printf("merge two file success\n");
    return 0;  
}   