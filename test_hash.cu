#include <stdint.h>
#include <string.h>
#include <cuda_runtime.h>
#include <stdio.h>

__device__ uint64_t R(uint64_t x,int n){return(x<<n)|(x>>(64-n));}

__device__ void keccakf(uint64_t st[25]){
    const uint64_t keccakf_rndc[24]={
        0x0000000000000001ULL,0x0000000000008082ULL,0x800000000000808aULL,
        0x8000000080008000ULL,0x000000000000808bULL,0x0000000080000001ULL,
        0x8000000080008081ULL,0x8000000000008009ULL,0x000000000000008aULL,
        0x0000000000000088ULL,0x0000000080008009ULL,0x000000008000000aULL,
        0x000000008000808bULL,0x800000000000008bULL,0x8000000000008089ULL,
        0x8000000000008003ULL,0x8000000000008002ULL,0x8000000000000080ULL,
        0x000000000000800aULL,0x800000008000000aULL,0x8000000080008081ULL,
        0x8000000000008080ULL,0x0000000080000001ULL,0x8000000080008008ULL
    };
    const int keccakf_rotc[24]={1,3,6,10,15,21,28,36,45,55,2,14,27,41,56,8,25,43,62,18,39,61,20,44};
    const int keccakf_piln[24]={10,7,11,17,18,3,5,16,8,21,24,4,15,23,19,13,12,2,20,14,22,9,6,1};
    uint64_t t,bc[5];
    for(int r=0;r<24;r++){
        // Theta
        for(int i=0;i<5;i++) bc[i]=st[i]^st[i+5]^st[i+10]^st[i+15]^st[i+20];
        for(int i=0;i<5;i++){
            t=bc[(i+4)%5]^R(bc[(i+1)%5],1);
            for(int j=0;j<25;j+=5) st[j+i]^=t;
        }
        // Rho Pi
        t=st[1];
        for(int i=0;i<24;i++){
            int j=keccakf_piln[i];
            bc[0]=st[j];
            st[j]=R(t,keccakf_rotc[i]);
            t=bc[0];
        }
        // Chi
        for(int j=0;j<25;j+=5){
            for(int i=0;i<5;i++) bc[i]=st[j+i];
            for(int i=0;i<5;i++) st[j+i]^=(~bc[(i+1)%5])&bc[(i+2)%5];
        }
        // Iota
        st[0]^=keccakf_rndc[r];
    }
}

__device__ void K256(const uint8_t*in,int inlen,uint8_t*out){
    uint64_t st[25]={0};
    uint8_t temp[136]={0};
    for(int i=0;i<inlen;i++) temp[i]=in[i];
    temp[inlen]=0x01;
    temp[135]^=0x80;
    for(int i=0;i<17;i++){
        uint64_t v=0;
        for(int j=0;j<8;j++) v|=((uint64_t)temp[i*8+j])<<(8*j);
        st[i]^=v;
    }
    keccakf(st);
    for(int i=0;i<32;i++) out[i]=(st[i/8]>>(8*(i%8)))&0xff;
}

__global__ void test_kernel(const uint8_t*in, uint8_t*out){
    K256(in,64,out);
}

int main(){
    uint8_t h_in[64]={
        0xbe,0xb2,0xd9,0x26,0x00,0x4e,0xa2,0x54,
        0xec,0x65,0x2b,0x97,0xcc,0x5a,0xd2,0x4d,
        0xe0,0xa0,0x5b,0xb0,0x77,0x22,0xc5,0xa5,
        0x37,0xe5,0xb6,0x47,0x60,0xc6,0xbb,0x4e,
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    };
    uint8_t h_out[32]={0};
    uint8_t *d_in,*d_out;
    cudaMalloc(&d_in,64);cudaMalloc(&d_out,32);
    cudaMemcpy(d_in,h_in,64,cudaMemcpyHostToDevice);
    test_kernel<<<1,1>>>(d_in,d_out);
    cudaDeviceSynchronize();
    cudaMemcpy(h_out,d_out,32,cudaMemcpyDeviceToHost);
    printf("CUDA    : ");
    for(int i=0;i<32;i++) printf("%02x",h_out[i]);
    printf("\nExpected: 0cb186b3202a6a5723c0e7610d5664af2862a742d748f6ee503a89b1974770fa\n");
    cudaFree(d_in);cudaFree(d_out);
}
