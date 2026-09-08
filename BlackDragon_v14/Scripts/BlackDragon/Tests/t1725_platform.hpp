// Explicit host API seam: not MQL5 ABI, MT5 runtime or broker evidence.
#include <algorithm>
#include <cmath>
#include <cstring>
#include <iostream>
#include <map>
#include <string>
#include <vector>
using string=std::string;using datetime=long;using uchar=unsigned char;
template<class T>void ZeroMemory(T&v){v=T{};}
template<class T,size_t N>void ZeroMemory(T(&v)[N]){for(auto &x:v)ZeroMemory(x);}
template<class T>int ArraySize(const std::vector<T>&v){return (int)v.size();}
template<class T>int ArrayResize(std::vector<T>&v,int n,int reserve=0){if(n<0)return -1;if(reserve>0&&n>(int)v.capacity())v.reserve(n+reserve);v.resize(n);return n;}
double MathAbs(double x){return std::abs(x);}double MathMax(double a,double b){return std::max(a,b);}double MathMin(double a,double b){return std::min(a,b);}double MathFloor(double x){return std::floor(x);}double MathRound(double x){return std::round(x);}
bool MathIsValidNumber(double x){return std::isfinite(x);}
int StringLen(const string&s){return s.size();}int StringGetCharacter(const string&s,int i){return (unsigned char)s.at(i);}
enum{INVALID_HANDLE=-1,FILE_BIN=1,FILE_READ=2,FILE_WRITE=4,FILE_REWRITE=8,ACCOUNT_LOGIN=1,MQL_TESTER=2,SYMBOL_VOLUME_STEP=3,SYMBOL_TRADE_TICK_SIZE=4};
long Magic=100,RecoveryMagic_=200;string _Symbol="fixture";bool RecoveryTesterResumeState_=true;
long AccountInfoInteger(int){return 123;}int MQLInfoInteger(int){return 0;}long nowMsc=100000;
long TimeCurrent(){return nowMsc/1000;}struct MqlTick{long time_msc;};bool SymbolInfoTick(const string&,MqlTick&t){t.time_msc=nowMsc;return true;}
double SymbolInfoDouble(const string&,int){return .01;}
std::map<string,std::vector<uchar>> files;struct Handle{string path;size_t at;};std::map<int,Handle> handles;
int nextHandle=1,writes=0,failWrite=0;bool failMove=false,failSeek=false;
bool FileIsExist(const string&p){return files.count(p);}
int FileOpen(const string&p,int flags){if(flags==(FILE_BIN|FILE_WRITE))files[p].clear();if(!files.count(p))return -1;int h=nextHandle++;handles[h]={p,0};return h;}
void FileClose(int h){handles.erase(h);}void FileFlush(int){}
ulong FileSize(int h){return files.at(handles.at(h).path).size();}ulong FileTell(int h){return handles.at(h).at;}
bool FileSeek(int h,long pos,int origin){if(failSeek||pos<0||origin!=SEEK_SET)return false;handles.at(h).at=pos;return true;}
template<class T>uint FileWriteStruct(int h,const T&v){auto &f=handles.at(h);auto &b=files[f.path];size_t n=sizeof(T);if(++writes==failWrite)n--;if(b.size()<f.at+n)b.resize(f.at+n);std::memcpy(b.data()+f.at,&v,n);f.at+=n;return n;}
template<class T>uint FileReadStruct(int h,T&v){auto&f=handles.at(h);auto&b=files.at(f.path);size_t n=std::min(sizeof(T),f.at<b.size()?b.size()-f.at:0);if(n)std::memcpy(&v,b.data()+f.at,n);f.at+=n;return n;}
uint FileWriteLong(int h,long v){return FileWriteStruct(h,v);}long FileReadLong(int h){long v=0;FileReadStruct(h,v);return v;}
uint FileReadArray(int h,std::vector<uchar>&v,int from,int count){auto&f=handles.at(h);auto&b=files.at(f.path);if(from<0||count<0||from+count>(int)v.size())return 0;size_t n=std::min((size_t)count,f.at<b.size()?b.size()-f.at:0);if(n)std::memcpy(v.data()+from,b.data()+f.at,n);f.at+=n;return n;}
bool FileMove(const string&from,int,const string&to,int){if(failMove||!files.count(from))return false;files[to]=files[from];files.erase(from);return true;}
enum{BD_M_PERSIST_BYTES,BD_M_SORT_ITEMS,BD_M_ALLOC_BYTES,BD_M_RECONCILE};struct Metrics{void Add(int,ulong=1){}}g_bdMetrics;
int passed=0,failed=0;void Check(const string&s,bool ok){if(ok)passed++;else{failed++;std::cout<<"FAIL: "<<s<<"\n";}}
int Finish(const string &name){std::cout<<"T17.25 "<<name<<": "<<passed<<" passed, "<<failed<<" failed\n";return failed?1:0;}
