#ifndef BD_ATOMIC_SNAPSHOT_MQH
#define BD_ATOMIC_SNAPSHOT_MQH
// POD payload envelope shared by the operation store and ARCS checkpoint.
// Final file is changed only after a complete temp payload and checksum exist.
struct SBDAtomicHeader
{
   uint magic,version,symbol,semantics,checksum;
   long account,core,hedge,sequence,payload;
   int records,epochs;
};
uint BD_HashText(const string s)
{ uint h=2166136261; for(int i=0;i<StringLen(s);i++){h^=(uint)StringGetCharacter(s,i);h*=16777619;} return h; }
uint BD_HashBytes(const uchar &bytes[])
{ uint h=2166136261; for(int i=0;i<ArraySize(bytes);i++){h^=(uint)bytes[i];h*=16777619;} return h; }
void BD_AtomicIdentity(SBDAtomicHeader &h,const uint magic,const uint version,const uint semantics)
{
   ZeroMemory(h);h.magic=magic;h.version=version;h.semantics=semantics;
   h.account=AccountInfoInteger(ACCOUNT_LOGIN);h.symbol=BD_HashText(_Symbol);
   h.core=(long)Magic;h.hedge=(long)RecoveryMagic_;
}
bool BD_AtomicIdentityMatches(const SBDAtomicHeader &a,const SBDAtomicHeader &b)
{ return a.magic==b.magic && a.version==b.version && a.account==b.account &&
         a.symbol==b.symbol && a.core==b.core && a.hedge==b.hedge && a.semantics==b.semantics; }
int BD_AtomicBegin(const string path,const SBDAtomicHeader &h)
{
   int f=FileOpen(path+".tmp",FILE_BIN|FILE_WRITE);
   if(f==INVALID_HANDLE)return f;
   if(FileWriteStruct(f,h)!=sizeof(SBDAtomicHeader)){FileClose(f);return INVALID_HANDLE;}
   return f;
}
bool BD_AtomicCommit(const string path,const int f,SBDAtomicHeader &h,const bool payloadOk)
{
   FileFlush(f);long size=(long)FileSize(f)-(long)sizeof(SBDAtomicHeader);FileClose(f);
   if(!payloadOk || size<0 || size>67108864)return false;
   int r=FileOpen(path+".tmp",FILE_BIN|FILE_READ|FILE_WRITE);if(r==INVALID_HANDLE)return false;
   uchar bytes[];bool ok=ArrayResize(bytes,(int)size)==(int)size;
   ok=ok && FileSeek(r,(long)sizeof(SBDAtomicHeader),SEEK_SET) && FileReadArray(r,bytes,0,(int)size)==(uint)size;
   if(ok){h.payload=size;h.checksum=BD_HashBytes(bytes);ok=FileSeek(r,0,SEEK_SET) && FileWriteStruct(r,h)==sizeof(SBDAtomicHeader);}
   FileFlush(r);FileClose(r);
   return ok && FileMove(path+".tmp",0,path,FILE_REWRITE);
}
int BD_AtomicOpen(const string path,const SBDAtomicHeader &identity,SBDAtomicHeader &h)
{
   int f=FileOpen(path,FILE_BIN|FILE_READ);if(f==INVALID_HANDLE)return f;
   bool ok=FileReadStruct(f,h)==sizeof(SBDAtomicHeader) && BD_AtomicIdentityMatches(h,identity) &&
      h.sequence>=0 && h.payload>=0 && h.payload<=67108864 && h.records>=0 && h.records<=65536 &&
      h.epochs>=0 && h.epochs<=65536 && (long)FileSize(f)==(long)sizeof(SBDAtomicHeader)+h.payload;
   uchar bytes[];
   if(ok)ok=ArrayResize(bytes,(int)h.payload)==(int)h.payload && FileReadArray(f,bytes,0,(int)h.payload)==(uint)h.payload && BD_HashBytes(bytes)==h.checksum;
   if(ok)ok=FileSeek(f,(long)sizeof(SBDAtomicHeader),SEEK_SET);
   if(!ok){FileClose(f);return INVALID_HANDLE;}return f;
}
#endif
