#include <stdio.h>  
#include <unistd.h>   
#include <sys/stat.h>  
#include <string.h> 
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

  
int create_file(char *s)
{
    FILE *fp;
    if(s==NULL||s[0]=='\0') return -1;//参数为空，即错误参数。
    fp= fopen(s, "r");//以只读方式打开
    if(fp)//打开成功，表示文件已经存在。
    {
        fclose(fp);//关闭文件
        return 1;//返回文件已存在。 
    }
    fp= fopen(s, "w");//以只写方式创建文件。
    if(fp == NULL) 
        return 2;//创建失败。
    fclose(fp);//关闭文件。
    return 0;//创建成功。
}
 
int main(int argc, char **argv)  
{
    printf("fileName:%s\n",argv[1]);

    char filepath[50];
    strcpy(filepath,argv[1]);  
    mkdirs(dirname(argv[1]));

    create_file(filepath);
    printf("create files success\n");  
    return 0;  
}  

