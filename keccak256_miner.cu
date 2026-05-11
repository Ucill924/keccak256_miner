#include <stdint.h>
#include <string.h>
#include <cuda_runtime.h>

__device__ uint64_t R(uint64_t x,int n){return(x<<n)|(x>>(64-n));}

__device__ void keccakf(uint64_t st[25]){
    const uint64_t rndc[24]={
        0x0000000000000001ULL,0x0000000000008082ULL,0x800000000000808aULL,
        0x8000000080008000ULL,0x000000000000808bULL,0x0000000080000001ULL,
        0x8000000080008081ULL,0x8000000000008009ULL,0x000000000000008aULL,
        0x0000000000000088ULL,0x0000000080008009ULL,0x000000008000000aULL,
        0x000000008000808bULL,0x800000000000008bULL,0x8000000000008089ULL,
        0x8000000000008003ULL,0x8000000000008002ULL,0x8000000000000080ULL,
        0x000000000000800aULL,0x800000008000000aULL,0x8000000080008081ULL,
        0x8000000000008080ULL,0x0000000080000001ULL,0x8000000080008008ULL
    };
    const int rotc[24]={1,3,6,10,15,21,28,36,45,55,2,14,27,41,56,8,25,43,62,18,39,61,20,44};
    const int piln[24]={10,7,11,17,18,3,5,16,8,21,24,4,15,23,19,13,12,2,20,14,22,9,6,1};
    uint64_t t,bc[5];
    for(int r=0;r<24;r++){
        for(int i=0;i<5;i++) bc[i]=st[i]^st[i+5]^st[i+10]^st[i+15]^st[i+20];
        for(int i=0;i<5;i++){t=bc[(i+4)%5]^R(bc[(i+1)%5],1);for(int j=0;j<25;j+=5)st[j+i]^=t;}
        t=st[1];
        for(int i=0;i<24;i++){int j=piln[i];bc[0]=st[j];st[j]=R(t,rotc[i]);t=bc[0];}
        for(int j=0;j<25;j+=5){for(int i=0;i<5;i++)bc[i]=st[j+i];for(int i=0;i<5;i++)st[j+i]^=(~bc[(i+1)%5])&bc[(i+2)%5];}
        st[0]^=rndc[r];
    }
}

__device__ void K256(const uint8_t*in,int inlen,uint8_t*out){
    uint64_t st[25]={0};
    uint8_t temp[136]={0};
    for(int i=0;i<inlen;i++) temp[i]=in[i];
    temp[inlen]=0x01;
    temp[135]^=0x80;
    for(int i=0;i<17;i++){uint64_t v=0;for(int j=0;j<8;j++)v|=((uint64_t)temp[i*8+j])<<(8*j);st[i]^=v;}
    keccakf(st);
    for(int i=0;i<32;i++) out[i]=(st[i/8]>>(8*(i%8)))&0xff;
}

__device__ bool hash_less_than(const uint8_t*h, const uint8_t*diff){
    for(int i=0;i<32;i++){
        if(h[i]<diff[i]) return true;
        if(h[i]>diff[i]) return false;
    }
    return false; // equal = not valid
}

__global__ void mine(
    const uint8_t*ch, const uint8_t*diff,
    const uint8_t*base_nonce,
    uint64_t bs, volatile int*found, uint8_t*res)
{
    uint64_t tid=(uint64_t)blockIdx.x*blockDim.x+threadIdx.x;
    if(tid>=bs||*found) return;

    uint8_t nonce[32];
    for(int i=0;i<32;i++) nonce[i]=base_nonce[i];
    // increment last 8 bytes by tid
    uint64_t lo=0;
    for(int i=0;i<8;i++) lo=(lo<<8)|nonce[24+i];
    lo+=tid;
    for(int i=0;i<8;i++) nonce[31-i]=(lo>>(i*8))&0xff;

    uint8_t in[64],h[32];
    for(int i=0;i<32;i++) in[i]=ch[i];
    for(int i=0;i<32;i++) in[32+i]=nonce[i];
    K256(in,64,h);

    if(hash_less_than(h,diff)){
        if(atomicCAS((int*)found,0,1)==0){
            for(int j=0;j<32;j++) res[j]=nonce[j];
        }
    }
}

extern "C"{
int launch_miner(const uint8_t*ch,const uint8_t*diff,const uint8_t*base_nonce,uint64_t bs,uint8_t*out){
    uint8_t*dc,*dd,*dn,*db; int*df;
    cudaMalloc(&dc,32);cudaMalloc(&dd,32);cudaMalloc(&dn,32);cudaMalloc(&db,32);cudaMalloc(&df,4);
    cudaMemcpy(dc,ch,32,cudaMemcpyHostToDevice);
    cudaMemcpy(dd,diff,32,cudaMemcpyHostToDevice);
    cudaMemcpy(db,base_nonce,32,cudaMemcpyHostToDevice);
    cudaMemset(df,0,4);cudaMemset(dn,0,32);
    int tb=256,bl=(int)((bs+255)/256);if(bl>65535)bl=65535;
    mine<<<bl,tb>>>(dc,dd,db,bs,df,dn);
    cudaDeviceSynchronize();
    int f=0;
    cudaMemcpy(&f,df,4,cudaMemcpyDeviceToHost);
    cudaMemcpy(out,dn,32,cudaMemcpyDeviceToHost);
    cudaFree(dc);cudaFree(dd);cudaFree(dn);cudaFree(db);cudaFree(df);
    return f;
}
}
