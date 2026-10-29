#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <climits>
#include <vector>
#include <string>
#include <array>
#include <map>
#include <set>
#include <algorithm>
#include <numeric>
#include <functional>
#include <random>
#include <fstream>
#include <iostream>
#include <sstream>
#include <utility>
using namespace std;
using namespace std;
const int NC=9,HMAX=12; int H=12;
int MAXM[NC]={4,6,8,10,12,10,8,6,4};
int DMG[NC]={3,2,2,1,1,1,2,2,3};
int GUARD=0; double GW=0; int WKT=0,WKC=0,WKR=0; double WMULT=2,WVAL=0; int NHZ=0; double HV=0; int HZMODE=1; int HZ[9][13]; int FUMC=0;
int FREE=0; int FAT=0, FATMODE=0, FATTRIG=0; bool freed[9]; double COMBO=0.0; double BVAL[6]={0,0,0,0,0,1};
int sumcol[13];
int R=3; int MAXRUN=1; int BONUS[NC][HMAX+1]; // 0 none, 1 common(wild if COMMONWILD) ...
bool COMMONWILD=false; int POLICY=0; int STRIKES=1, ROLLCAP=1000, SAFE=0; // 0 damage-max, 1 step-max
struct St{int8_t h[NC];uint16_t run;int8_t placed,Reff;};
int LOCKM=0, GRAPM=0; // keyword masks: Lock = no runners of any kind; Grapple = no wild or surge steps
inline bool legal(const St&s,int c){return !((LOCKM>>c)&1)&&s.h[c]<H&&(((s.run>>c)&1)||s.placed<s.Reff);}
inline void app(St&s,int c){if(!((s.run>>c)&1)){s.run|=1<<c;s.placed++;}s.h[c]++;}
int guardOf(const int8_t*h){ if(GUARD==4){int g=0;for(int c=3;c<=5;c++)for(int r=1;r<=h[c];r++)if(BONUS[c][r]!=5)g++;return g;} if(GUARD==1)return h[4]; if(GUARD==2)return (h[3]+h[4]+h[5])/2; if(GUARD==3)return h[3]+h[4]+h[5]; return 0;}
int RR=0; double WMULT2=3,WVAL2=0; double EVADE=0; int WCOL=0; double WCOLM=2; int WFLAT=0, WSTEPS=0; bool wdone[9];
int weakOf(const int8_t*h){ if(WKT==1)return h[WKC]>=WKR; if(WKT==2)return h[WKC]>=WKR&&h[8-WKC]>=WKR; if(WKT==3){if(WKC==4)return h[4]>=WKR; return (h[WKC]>=WKR)+(h[8-WKC]>=WKR);} return 0;}
inline double W(int c){double w=POLICY==0?DMG[c]+COMBO:1.0; if(GUARD==1&&c==4)w+=GW; if(GUARD==2&&c>=3&&c<=5)w+=GW/2; if((GUARD==3||GUARD==4)&&c>=3&&c<=5)w+=GW; return w;}
struct Opt{St s;double g;};
void rec(const St&s,const vector<int>&tk,size_t i,int adv,double g,vector<Opt>&out,vector<int>&advs){
  if(i==tk.size()){out.push_back({s,g});advs.push_back(adv);return;}
  int c=tk[i];
  if(c==-2){rec(s,tk,i+1,adv,g,out,advs);return;}
  if(c<0){bool any=false;for(int x=0;x<NC;x++)if(legal(s,x)&&!((GRAPM>>x)&1)){any=true;St n=s;app(n,x);rec(n,tk,i+1,adv+1,g+W(x),out,advs);}if(!any)rec(s,tk,i+1,adv,g,out,advs);}
  else if(legal(s,c)){St n=s;app(n,c);rec(n,tk,i+1,adv+1,g+W(c),out,advs);}
  else rec(s,tk,i+1,adv,g,out,advs);
}
void gen(const St&s,const int*d,vector<Opt>&out){
  out.clear();vector<int> advs;
  static const int P[3][4]={{0,1,2,3},{0,2,1,3},{0,3,1,2}};
  for(int p=0;p<3;p++){vector<int> tk={sumcol[d[P[p][0]]+d[P[p][1]]],sumcol[d[P[p][2]]+d[P[p][3]]]};sort(tk.begin(),tk.end());
    do{rec(s,tk,0,0,0,out,advs);}while(next_permutation(tk.begin(),tk.end()));}
  int mx=0;for(int a:advs)mx=max(mx,a);vector<Opt> f;for(size_t i=0;i<out.size();i++)if(advs[i]==mx&&mx>0)f.push_back(out[i]);out.swap(f);
}
struct BG{float b,g;};unordered_map<uint32_t,BG> cache;
uint32_t keyOf(const St&s){uint32_t um=0;for(int c=0;c<NC;c++)if(s.h[c]>=H)um|=1u<<c;return s.run|(um<<9)|(s.placed<<18)|(s.Reff<<22);}
BG getBG(const St&s){uint32_t k=keyOf(s);auto it=cache.find(k);if(it!=cache.end())return it->second;
  St t=s;for(int c=0;c<NC;c++)t.h[c]=(s.h[c]>=H)?H:0;double bust=0,gs=0,nb=0;vector<Opt> out;int d[4];
  for(d[0]=1;d[0]<=6;d[0]++)for(d[1]=1;d[1]<=6;d[1]++)for(d[2]=1;d[2]<=6;d[2]++)for(d[3]=1;d[3]<=6;d[3]++){
    gen(t,d,out);if(out.empty()){bust++;continue;}double bg=0;for(auto&o:out)bg=max(bg,o.g);gs+=bg;nb++;}
  BG r{(float)(bust/1296),(float)(nb>0?gs/nb:0)};cache[k]=r;return r;}
double score(const St&s,double now){BG g=getBG(s);double fut=min((1-g.b)/max((double)g.b,0.03),30.0);return now+fut*g.g;}
double valueOf(const St&s){double v=0;for(int c=0;c<NC;c++){v+=s.h[c]*(POLICY==0?DMG[c]+COMBO:1.0);for(int r=1;r<=s.h[c];r++){v+=BVAL[BONUS[c][r]];v-=HV*HZ[c][r];}}
  v+=GW*guardOf(s.h); int wn=weakOf(s.h); if(wn==2)v+=WVAL2; else if(wn==1)v+=WVAL;
  if(WKT==3&&WVAL>0){ int a=min((int)s.h[WKC],WKR), b=min((int)s.h[8-WKC],WKR); if(wn==0) v+=0.6*WVAL*max(a,b)/(double)WKR; else if(wn==1&&WKC!=4) v+=0.5*(WVAL2-WVAL)*min(a,b)/(double)WKR; }
  else if(wn==0&&WVAL>0){ if(WKT==1) v+=0.6*WVAL*min((int)s.h[WKC],WKR)/(double)WKR;
                   if(WKT==2) v+=0.3*WVAL*(min((int)s.h[WKC],WKR)+min((int)s.h[8-WKC],WKR))/(double)WKR; }
  return v;}
mt19937_64 rng(5);
struct RunRes{int h[NC];int guard,weak,hzhit,evaded,trapped,topcol,rrused;long long mask;int rolls,dmg,bonus[6],maxbonus,wilds212,busts,throws,fumble,danger,wild;};
bool maxDone[NC];
void awards(St&s,bool&maxUsed,bool*bonDone,RunRes&rr){
  bool again=true;while(again){again=false;
    if(WSTEPS&&WKT==3){int cs2[2]={WKC,8-WKC};for(int k=0;k<(WKC==4?1:2);k++){int c=cs2[k];if(s.h[c]>=WKR&&!wdone[c]){wdone[c]=true;again=true;
        for(int st=0;st<WSTEPS;st++){double bs=-1;int bc=-1;for(int x=0;x<NC;x++)if(legal(s,x)){St n=s;app(n,x);double sc=score(n,valueOf(n));if(sc>bs){bs=sc;bc=x;}}if(bc>=0)app(s,bc);}}}}
    for(int c=0;c<NC;c++){
      if(FREE&&s.h[c]>=H&&((s.run>>c)&1)&&!freed[c]){freed[c]=true;s.placed--;again=true;}
      // bonus squares crossed
      for(int r=1;r<=s.h[c];r++) if(BONUS[c][r]&&!bonDone[c*16+r]){bonDone[c*16+r]=true;rr.bonus[BONUS[c][r]]++;again=true;
        if(COMMONWILD&&BONUS[c][r]==1){double bs=-1;int bc=-1;for(int x=0;x<NC;x++)if(legal(s,x)){St n=s;app(n,x);double sc=score(n,valueOf(n));if(sc>bs){bs=sc;bc=x;}}if(bc>=0)app(s,bc);}}
      if(MAXRUN==1&&!maxUsed&&s.h[c]>=MAXM[c]&&((s.run>>c)&1)){maxUsed=true;again=true;rr.maxbonus++;s.Reff++;
        double bs=-1;int bc=-1;for(int x=0;x<NC;x++){if(s.h[x]>=H||((s.run>>x)&1)||((LOCKM>>x)&1)||((GRAPM>>x)&1))continue;St n=s;app(n,x);double sc=score(n,valueOf(n));if(sc>bs){bs=sc;bc=x;}}
        if(bc>=0)app(s,bc);}
      if(MAXRUN>=2&&s.h[c]>=MAXM[c]&&((s.run>>c)&1)&&!maxDone[c]&&!(MAXRUN==2&&maxUsed)){maxDone[c]=true;maxUsed=true;again=true;rr.maxbonus++;
        for(int k=0;k<(MAXRUN==4?2:1);k++){double bs=-1;int bc=-1;for(int x=0;x<NC;x++)if(legal(s,x)&&!((GRAPM>>x)&1)){St n=s;app(n,x);double sc=score(n,valueOf(n));if(sc>bs){bs=sc;bc=x;}}if(bc>=0)app(s,bc);}}
    }}
}
int INITH[9]={0};
RunRes run(){
  memset(HZ,0,sizeof HZ);{uniform_int_distribution<int> d6(1,6);for(int k=0;k<NHZ;k++){int c,r;do{int sm=d6(rng)+d6(rng);if(sm<3||sm>11)continue;c=sm-3;r=d6(rng);if(!HZ[c][r]&&!BONUS[c][r])break;}while(true);HZ[c][r]=1;}}
  St s;for(int c=0;c<NC;c++)s.h[c]=INITH[c];s.run=0;s.placed=0;s.Reff=R;RunRes rr;memset(&rr,0,sizeof rr);
  bool maxUsed=false;bool bonDone[NC*16]={0};memset(maxDone,0,sizeof maxDone);memset(freed,0,sizeof freed);memset(wdone,0,sizeof wdone);for(int c=0;c<NC;c++){for(int r=1;r<=INITH[c];r++)bonDone[c*16+r]=true;if(INITH[c]>=MAXM[c]){maxDone[c]=true;}if(INITH[c]>=H)freed[c]=true;}vector<Opt> out;int d[4];uniform_int_distribution<int> die(1,6);
  int strikes=0, rerolls=0;
  while(true){if(rr.rolls>=ROLLCAP)break;for(int i=0;i<4;i++)d[i]=die(rng);rr.throws++;
    bool fatOn=false;
    if(FAT||FATTRIG){ if(FATTRIG==0) fatOn=(rr.rolls+1>=FAT);
      else if(FATTRIG==1){for(int c=0;c<NC;c++)if(s.h[c]>=FAT)fatOn=true;}
      else {for(int c=0;c<NC;c++)if(s.h[c]>=MAXM[c])fatOn=true;}
      if(rr.rolls+1<=SAFE)fatOn=false; }
    if(fatOn)rr.danger=1;
    if(fatOn){int cnt[7]={0};for(int i=0;i<4;i++)cnt[d[i]]++;int pr=0,tr=0;for(int v=1;v<=6;v++){pr+=cnt[v]/2;if(cnt[v]>=3)tr=1;}
      bool f=(FATMODE==1)?(pr>=2||tr):(FATMODE==2)?(pr>=1):(FATMODE==3)?(tr==1):false; if(f){ if(rerolls<RR){rerolls++;rr.rrused++;continue;} rr.busts++;rr.fumble=1;break;}}
    gen(s,d,out);if(out.empty()){ if(rr.rolls<SAFE)continue; if(rerolls<RR){rerolls++;rr.rrused++;continue;} strikes++; rr.busts++; if(strikes>=STRIKES)break; continue;}
    double best=-1;int bi=0;for(size_t i=0;i<out.size();i++){double sc=score(out[i].s,valueOf(out[i].s));if(sc>best){best=sc;bi=i;}}
    s=out[bi].s;rr.rolls++;awards(s,maxUsed,bonDone,rr);
    if(HZMODE==2){bool tr=false;for(int c=0;c<NC;c++)for(int r=1;r<=s.h[c];r++)if(HZ[c][r]==1){ if(uniform_real_distribution<double>(0,1)(rng)<EVADE){HZ[c][r]=2;rr.evaded++;} else tr=true;} if(tr){rr.fumble=1;rr.trapped=1;break;}}}
  for(int c=0;c<NC;c++){rr.h[c]=s.h[c];rr.dmg+=s.h[c]*DMG[c];for(int r=1;r<=s.h[c];r++){if(BONUS[c][r]==5)rr.dmg++;if(HZ[c][r])rr.hzhit++;}}
  rr.topcol=0; for(int c=0;c<NC;c++){int v=s.h[c]*DMG[c];for(int r=1;r<=s.h[c];r++)if(BONUS[c][r]==5)v++; if(v>rr.topcol)rr.topcol=v;}
  rr.mask=0; {int k=0; for(int c=0;c<NC;c++)for(int r=1;r<=H;r++)if(BONUS[c][r]>=1&&BONUS[c][r]<=4){ if(s.h[c]>=r)rr.mask|=(1LL<<k); k++; }}
  rr.guard=guardOf(s.h); rr.weak=weakOf(s.h);
  if(WCOL){ int ex=0; int cs[2]={WKC,8-WKC}; for(int k=0;k<(WKC==4?1:2);k++){int c=cs[k]; if(s.h[c]>=WKR){ex+=s.h[c]*DMG[c];for(int r=1;r<=s.h[c];r++)if(BONUS[c][r]==5)ex++;}}
    if(rr.weak==1)rr.dmg+=(int)(ex*(WCOLM-1)+0.5)+WFLAT; else if(rr.weak==2)rr.dmg=(int)((rr.dmg)*WMULT2+0.5)+WFLAT; }
  else { if(rr.weak==1)rr.dmg=(int)(rr.dmg*WMULT+0.5); else if(rr.weak==2)rr.dmg=(int)(rr.dmg*WMULT2+0.5); }return rr;
}
int main(int argc,char**argv){
  int N=atoi(argv[1]);POLICY=atoi(argv[2]);COMMONWILD=atoi(argv[3]);const char*layout=(argc>4&&strcmp(argv[4],"-"))?argv[4]:nullptr;if(argc>5)STRIKES=atoi(argv[5]);if(argc>6)ROLLCAP=atoi(argv[6]);if(argc>7)SAFE=atoi(argv[7]);if(argc>8)MAXRUN=atoi(argv[8]);if(argc>9&&atoi(argv[9])==1){int nd[9]={2,1,1,0,0,0,1,1,2};for(int i=0;i<9;i++)DMG[i]=nd[i];COMBO=0.5;BVAL[1]=1.5;}if(argc>10){FREE=atoi(argv[10]);BVAL[2]=3;BVAL[3]=5;BVAL[4]=8;}
  for(int s=3;s<=11;s++)sumcol[s]=s-3;sumcol[2]=sumcol[12]=-1;
  memset(BONUS,0,sizeof BONUS);
  if(layout){FILE*f=fopen(layout,"r");int c,r,t;while(fscanf(f,"%d %d %d",&c,&r,&t)==3)BONUS[c][r]=t;fclose(f);}
  if(argc>12){H=atoi(argv[12]);int base[9]={4,6,8,10,12,10,8,6,4};for(int c=0;c<NC;c++)MAXM[c]=(int)floor(base[c]*H/12.0+0.5);}
  if(argc>13&&atoi(argv[13])==0){sumcol[2]=sumcol[12]=-2;}
  if(argc>18){int L=atoi(argv[18]); if(L==311){sumcol[3]=sumcol[11]=-2;} else if(L==68){sumcol[6]=sumcol[8]=-2;}
    else if(L==678){sumcol[6]=sumcol[7]=sumcol[8]=-2;} else if(L==759){sumcol[7]=sumcol[5]=sumcol[9]=-2;} else if(L==7410){sumcol[7]=sumcol[4]=sumcol[10]=-2;} else if(L==7311){sumcol[7]=sumcol[3]=sumcol[11]=-2;} else if(L>0){sumcol[L]=-2;}}
  if(argc>19){int pf=atoi(argv[19]); if(pf==1){DMG[0]=DMG[8]=1;} if(pf==2){DMG[1]=DMG[2]=DMG[6]=DMG[7]=0;} if(pf==3){DMG[3]=DMG[4]=DMG[5]=1;}}
  if(argc>14){R=atoi(argv[14]);}
  if(argc>15){FAT=atoi(argv[15]);FATMODE=atoi(argv[16]);}if(argc>17)FATTRIG=atoi(argv[17]);
  if(argc>20){GUARD=atoi(argv[20]);GW=atof(argv[21]);}
  if(argc>22){WKT=atoi(argv[22]);WKC=atoi(argv[23]);WKR=atoi(argv[24]);WMULT=atof(argv[25]);WVAL=atof(argv[26]);}
  if(argc>27){NHZ=atoi(argv[27]);HV=atof(argv[28]);}if(argc>30)HZMODE=atoi(argv[30]);if(argc>31)EVADE=atof(argv[31]);if(argc>32){WMULT2=atof(argv[32]);WVAL2=atof(argv[33]);}if(argc>34)WCOL=atoi(argv[34]);if(argc>35)WCOLM=atof(argv[35]);if(argc>36)WFLAT=atoi(argv[36]);if(argc>37)WSTEPS=atoi(argv[37]);if(argc>38)RR=atoi(argv[38]);if(argc>40){LOCKM=atoi(argv[39]);GRAPM=atoi(argv[40]);}if(argc>49){for(int i=0;i<9;i++)DMG[i]=atoi(argv[41+i]);}
  const char* DUMP=argc>29?argv[29]:nullptr;
  int CONT=argc>11?atoi(argv[11]):0;
  if(CONT==6){FILE*o=fopen(DUMP,"w");for(int i=0;i<N;i++){RunRes a=run();fprintf(o,"%d %d %d %d %d %d %d %d %d %lld",a.dmg,a.guard,a.fumble,a.weak,a.hzhit,a.rolls,a.evaded,a.trapped,a.topcol,a.mask);for(int c=0;c<NC;c++)fprintf(o," %d",a.h[c]);fprintf(o," %d\n",a.rrused);}fclose(o);return 0;}
  if(CONT==8){
    long cnt[6][6]={{0}};long any=0,fum=0,dang=0,surge1=0;double surge=0;long hdist[5][1]={{0}};
    vector<double> dm,rl;long dh[60]={0},rh[40]={0};long colsUsed[10]={0};double colm[NC]={0};
    static long reach[NC][HMAX+1];memset(reach,0,sizeof reach);
    for(int i=0;i<N;i++){RunRes a=run();dm.push_back(a.dmg);rl.push_back(a.rolls);dh[min(59,a.dmg)]++;rh[min(39,a.rolls)]++;
      int tot=0;for(int k=1;k<5;k++){cnt[k][min(5,a.bonus[k])]++;tot+=a.bonus[k];}if(tot>0)any++;
      fum+=a.fumble;dang+=a.danger;surge+=a.maxbonus;if(a.maxbonus>0)surge1++;
      int u=0;for(int c=0;c<NC;c++){if(a.h[c]>0)u++;colm[c]+=a.h[c];for(int r=1;r<=a.h[c];r++)reach[c][r]++;}colsUsed[u]++;}
    auto pc=[&](double x){return 100.0*x/N;};
    sort(dm.begin(),dm.end());sort(rl.begin(),rl.end());double md=0,mr=0;for(double x:dm)md+=x;for(double x:rl)mr+=x;md/=N;mr/=N;
    double sd=0;for(double x:dm)sd+=(x-md)*(x-md);sd=sqrt(sd/N);
    printf("DMG mean=%.2f sd=%.2f p5=%.0f p10=%.0f p25=%.0f p50=%.0f p75=%.0f p90=%.0f p95=%.0f p99=%.0f max=%.0f\n",md,sd,dm[N/20],dm[N/10],dm[N/4],dm[N/2],dm[3*N/4],dm[9*N/10],dm[19*N/20],dm[99*N/100],dm[N-1]);
    printf("ROLLS mean=%.2f p5=%.0f p10=%.0f p25=%.0f p50=%.0f p75=%.0f p90=%.0f p95=%.0f p99=%.0f max=%.0f\n",mr,rl[N/20],rl[N/10],rl[N/4],rl[N/2],rl[3*N/4],rl[9*N/10],rl[19*N/20],rl[99*N/100],rl[N-1]);
    printf("END: bust=%.1f%% fumble=%.1f%% | danger line reached=%.1f%%\n",pc(N-fum),pc(fum),pc(dang));
    printf("SURGE: mean=%.2f P(>=1)=%.1f%%\n",surge/N,pc(surge1));
    const char*nm[5]={"","common","uncommon","rare","legendary"};
    for(int k=1;k<5;k++){long ge1=N-cnt[k][0];printf("%s: P(>=1)=%.1f%% dist0=%.1f 1=%.1f 2=%.1f 3=%.1f 4+=%.1f\n",nm[k],pc(ge1),pc(cnt[k][0]),pc(cnt[k][1]),pc(cnt[k][2]),pc(cnt[k][3]),pc(cnt[k][4]+cnt[k][5]));}
    printf("ANY bonus: %.1f%%\n",pc(any));
    printf("COLS used:");for(int u=0;u<=6;u++)printf(" %d:%.1f",u,pc(colsUsed[u]));printf("\n");
    printf("COLMEAN:");for(int c=0;c<NC;c++)printf(" %.2f",colm[c]/N);printf("\n");
    printf("DMGHIST:");for(int i=0;i<=30;i++)printf(" %.2f",pc(dh[i]));printf("\n");
    printf("ROLLHIST:");for(int i=0;i<=24;i++)printf(" %.2f",pc(rh[i]));printf("\n");
    FILE*o=fopen("reach_final.txt","w");for(int r=H;r>=1;r--){for(int c=0;c<NC;c++)fprintf(o,"%.4f ",(double)reach[c][r]/N);fprintf(o,"\n");}fclose(o);
    return 0;}
  if(CONT==9){int hs[40]={0},ht[60]={0};double ms=0,mt=0;vector<int> vs,vt;
    for(int i=0;i<N;i++){RunRes a=run();hs[min(39,a.rolls)]++;ht[min(59,a.throws)]++;ms+=a.rolls;mt+=a.throws;vs.push_back(a.rolls);vt.push_back(a.throws);}
    sort(vs.begin(),vs.end());sort(vt.begin(),vt.end());
    printf("successful rolls mean=%.2f p10=%d p25=%d p50=%d p75=%d p90=%d\n",ms/N,vs[N/10],vs[N/4],vs[N/2],vs[3*N/4],vs[9*N/10]);
    printf("all throws mean=%.2f p10=%d p25=%d p50=%d p75=%d p90=%d\n",mt/N,vt[N/10],vt[N/4],vt[N/2],vt[3*N/4],vt[9*N/10]);
    printf("SUCC:");for(int i=0;i<=24;i++)printf(" %.2f",100.0*hs[i]/N);printf("\n");
    printf("THROW:");for(int i=0;i<=40;i++)printf(" %.2f",100.0*ht[i]/N);printf("\n");return 0;}
  if(CONT){vector<double> d1,d2;double b2[5]={0};
    for(int i=0;i<N;i++){memset(INITH,0,sizeof INITH);RunRes a=run();d1.push_back(a.dmg);
      if(CONT==1){for(int c=0;c<NC;c++)INITH[c]=a.h[c];}
      else{int bc=0;double bv=-1;for(int c=0;c<NC;c++){double v=a.h[c]*DMG[c];if(v>bv){bv=v;bc=c;}}memset(INITH,0,sizeof INITH);INITH[bc]=a.h[bc];}
      RunRes b=run();d2.push_back(b.dmg);for(int k=1;k<5;k++)b2[k]+=b.bonus[k];}
    auto st=[&](vector<double>&v,const char*nm){sort(v.begin(),v.end());double m=0;for(double x:v)m+=x;m/=v.size();printf("%s mean=%.2f p10=%.0f p50=%.0f p90=%.0f\n",nm,m,v[v.size()/10],v[v.size()/2],v[v.size()*9/10]);};
    st(d1,"attack1(fresh)");st(d2,"attack2(carried)");printf("attack2 new bonuses: C=%.2f U=%.2f R=%.2f L=%.2f\n",b2[1]/N,b2[2]/N,b2[3]/N,b2[4]/N);return 0;}
  static long reach[NC][HMAX+1];memset(reach,0,sizeof reach);vector<double> dm,rl;double bon[5]={0},mb=0;vector<int> legCount;
  double colmean[NC]={0};
  for(int i=0;i<N;i++){RunRes rr=run();for(int c=0;c<NC;c++){colmean[c]+=rr.h[c];for(int r=1;r<=rr.h[c];r++)reach[c][r]++;}
    dm.push_back(rr.dmg);rl.push_back(rr.rolls);for(int k=1;k<5;k++)bon[k]+=rr.bonus[k];mb+=rr.maxbonus;}
  sort(dm.begin(),dm.end());sort(rl.begin(),rl.end());double m=0,mr=0;for(double x:dm)m+=x;for(double x:rl)mr+=x;
  printf("dmg mean=%.2f p10=%.0f p25=%.0f p50=%.0f p75=%.0f p90=%.0f | rolls mean=%.2f p10=%.0f p50=%.0f p90=%.0f | maxbonus=%.3f\n",m/N,dm[N/10],dm[N/4],dm[N/2],dm[3*N/4],dm[9*N/10],mr/N,rl[N/10],rl[N/2],rl[9*N/10],mb/N);
  {double sd=0;for(double x:dm)sd+=(x-m/N)*(x-m/N);sd=sqrt(sd/N);printf("sd=%.1f cv=%.2f IQR=%.0f\n",sd,sd/(m/N),dm[3*N/4]-dm[N/4]);
   int H2[25]={0};for(double x:dm)H2[min(24,(int)(x/8))]++;printf("HIST8:");for(int i=0;i<25;i++)printf(" %.1f",100.0*H2[i]/N);printf("\n");
   int H3[20]={0};for(double x:dm)H3[min(19,(int)(x/3))]++;printf("HIST2:");{int H4[20]={0};for(double x:dm)H4[min(19,(int)(x/2))]++;for(int i=0;i<20;i++)printf(" %.1f",100.0*H4[i]/N);printf("\n");}printf("HIST3:");for(int i=0;i<20;i++)printf(" %.1f",100.0*H3[i]/N);printf("\n");}
  printf("bonus per run: common=%.3f uncommon=%.3f rare=%.3f legendary=%.3f\n",bon[1]/N,bon[2]/N,bon[3]/N,bon[4]/N);
  printf("colmean:");for(int c=0;c<NC;c++)printf(" %.2f",colmean[c]/N);printf("\n");
  FILE*o=fopen("reach.txt","w");for(int r=H;r>=1;r--){for(int c=0;c<NC;c++)fprintf(o,"%.4f ",(double)reach[c][r]/N);fprintf(o,"\n");}fclose(o);
}
