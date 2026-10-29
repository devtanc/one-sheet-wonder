import numpy as np, random
from functools import lru_cache
DUMP={}
import os as _os
D4 = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'd4')   # attack data lives beside the engine
def load(k):
    if k not in DUMP:
        path = _os.path.join(D4, f'{k}.npy')
        if k.startswith('kw') and not _os.path.exists(path):
            import kwboard; kwboard.generate(k)
        DUMP[k]=np.load(path).tolist()
    return DUMP[k]
SQ_RAR=['R','L','U','L','C','R','C','U','C','U','R','C','U','C','R','U','L','R','L']
@lru_cache(maxsize=None)
def bits(mask): return tuple(i for i in range(48) if mask>>i&1)
MYTHIC=['Meteor','Time Stop','Overdrive','Phoenix','Godslayer','Echo']
POOLS={'C':['Extra Attack','Brace','Mark'],
       'U':['Poison I','Ranged','Pickpocket','Cleave','Leech','Disarm'],
       'R':['Poison II','Sleep','Weaken','Momentum'],
       'L':['Critical Hit','Chain','Execute','Encore']}
P=dict(DEX_HALF=0, DEX_ARMOR=0, B_ABOVE=0, B_CTR=1, K_CARRY=0.0, PA_DIV=3, PA_HEAL=1, A_WEAK=0, A_CRIT=0, RG_PET=0, T_RR=0, E_FIRE=0, E_ARC=0, E_FROST=0, NC_DMG=0, NC_CAP=3, NC_START=0, WL_COST=0, WL_MIN=10, D_BEAR=2.5, D_CAT=2.0, D_POL='bossbear', IQ_DIV=3, W_OUTER=0.0, R_WEAK=0.0, M_SPELL=0.0, M_GUARD=2.0, C_DIV=0, C_SMITE=0.0, POOL_SCOPE='fight', DEX_REROLL=0, INT_IGNORE=0, STR_DMG=0, STR_GUARD=0, INT_WEAK=0, INT_OFFERS=0, INT_COUNTER=0, INT_RESIST=0.0, DEX_EVADE=0.0, BRACE_HEAVY=3, REMOVED={4,13}, RIPOSTE=4, RIP_CAP=1, SLEEP_GROGGY=1, ENCORE_SAFE=1, BRACE_MODE='heavy', SLEEP_TURNS=1, DISARM_TURNS=2, WEAKEN_CANCEL=0, RANGED_FALL=1, ONCE={'Extra Attack','Brace','Mark','Poison I','Ranged','Cleave','Pickpocket'}, P1=(1,2), P2=(2,4), CLEAVE_DIV=3, DISARM_HALF=0, WEAKEN_DUR=0, MOM_FRAC='ceil3', CHAIN_MULT=2.0, LEECH_DIV=5, LEECH_FLAT=0, LEECH_ONCE=1, PICK_DMG=1, CRIT=4.0, EXEC=8, EXECF=0.5, EXEC_FALL=15, ENCORE_BONUS=1, ENCORE=1, WEAKEN=3, BRACE=1, MARK=1, CHAIN_FALL=2.0, CLEAVE_FALL=0.5, GUARD_MULT=2.0, COUNTER=3, TACT_T=15)
def draw_offers(pools=POOLS, fixed=None):
    if fixed: return fixed
    off={}
    for r,v in pools.items():
        x=random.random(); k=1 if x<0.125 else (3 if x>0.875 else 2); k=min(k,len(v))
        off[r]=random.sample(v,k)
    return off
class E:
    def __init__(s,name,hp,intents,weak='w410',mode=None,profile=None,cover=False,boss=False):
        s.name=name;s.hp=hp;s.max=hp;s.intents=intents;s.weak=weak;s.mode=mode;s.profile=profile;s.cover=cover;s.boss=boss
        s.i=0;s.sleep=0;s.disarm=0;s.weaken=0;s.cancel=0;s.poison=[]
    def nxt(s): return s.intents[s.i%len(s.intents)]
# intent: dict(d=damage, heavy=bool, onhit=None|'poison'|'daze'|'pin'|'jinx', pierce=0..1, windup=bool)
def I(d,heavy=False,onhit=None,pierce=0.0): return dict(d=d,heavy=heavy,onhit=onhit,pierce=pierce)
TWISTS={'gate678':'R','ironwall':'C','shieldwall':'C','thickhide':'C','traps':'U','daze':'R','jinx':'U','plate':'U','pin':'L'}
OPENINGS={'exposed':'C','cracked':'L'}
PRESSURES={'berserk':'R','doom':'C','fortify':'C','regen':'C','frenzy':'U','haste':'R'}
W={'C':50,'U':30,'R':15,'L':5}
def wpick(d): ks=list(d); return random.choices(ks,[W[d[k]] for k in ks])[0]
def draw_phases(no_pin_pressure=True):
    while True:
        p2=(wpick(TWISTS), wpick(PRESSURES) if random.random()<0.5 else '')
        p3=(wpick(OPENINGS),wpick(PRESSURES)) if random.random()<2/3 else (wpick(TWISTS),wpick(PRESSURES))
        bad=any(t=='pin' and p for t,p in (p2,p3)) or any(t in ('jinx','plate','pin') and p in ('fortify','regen') for t,p in (p2,p3))
        if not (no_pin_pressure and bad): return [('normal',''),p2,p3]
KW_BOARD={'Daze','Pin','Trapper','Lock','Grapple','Taunt'}; KW_TARGET={'Bulk','Fractured','Plate','Exposed'}; KW_PRESS={'Frenzy','Fortify','Regen','Haste','Berserk'}
def kwx(k,default=0):
    t=[x for x in k.split()[1:] if x.isdigit()]; return int(t[0]) if t else default
PLUSSQ={(4,1),(3,3),(5,3),(4,6),(3,7),(5,7)}
DMGT={'thickhide':[1,1,1,0,0,0,1,1,1],'plate':[2,0,0,0,0,0,0,0,2],'cracked':[2,1,1,1,1,1,1,1,2]}
WEAKP={'w311':(0,6),'w410':(1,5),'w59':(2,6)}
def coldmg(h,c,mode):
    d=DMGT.get(mode,[2,1,1,0,0,0,1,1,2])[c]; return h[c]*d+sum(1 for r in range(1,h[c]+1) if (c,r) in PLUSSQ)
BASEOF={'Druid':'Cleric','Barbarian':'Warrior','Knight':'Warrior','Assassin':'Rogue','Ranger':'Rogue','Trickster':'Rogue','Elementalist':'Mage','Necromancer':'Mage','Warlock':'Mage','Inquisitor':'Cleric'}
TRACE=[]; TRACE_ON=False
def key(mode,pair,aim,st): return f"{mode}_{pair}_a{1 if aim else 0}_{st}"
def effect_value(ef,ctx):
    t=ctx['target']; top=ctx['top']; others=ctx['others']
    if ef=='Extra Attack': return 1.2
    if ef=='Brace': return (P['BRACE_HEAVY']*any(i and i['heavy'] for i in [ctx['tnext']]) if P['BRACE_MODE']=='heavy' else 1.6 if P['BRACE_MODE']=='counter' else min(P['BRACE'],max(0,ctx['incoming']-ctx['guard']))*1.0)
    if ef=='Mark': return P['MARK']
    if ef=='Poison I': return min(P['P1'][0]*P['P1'][1],max(0,t.hp-ctx['dmg']))
    if ef=='Poison II': return min(P['P2'][0]*P['P2'][1],max(0,t.hp-ctx['dmg']))
    if ef=='Ranged': return 2
    if ef=='Pickpocket': return 0.3+P['PICK_DMG']
    if ef=='Cleave': return top//P['CLEAVE_DIV'] if others else int(top/P['CLEAVE_DIV']*2*P['CLEAVE_FALL'])
    if ef=='Leech': h=(P['LEECH_FLAT'] or top//P['LEECH_DIV']); return min(h, ctx['maxhp']-ctx['hp'])*(1.5 if ctx['hp']<ctx['maxhp']*0.4 else 0.8)
    if ef=='Disarm': ni=ctx['tnext']; return ((ni['d']-t.intents[0]['d']) if ni and ni['heavy'] else 0.5)+((ni['d']//2) if (ni and P['DISARM_HALF']) else 0)
    if ef=='Sleep': ni=ctx['tnext']; return (ni['d'] if ni else 0)*0.8*P['SLEEP_TURNS']
    if ef=='Weaken': ni=ctx['tnext']; return (0 if t.weaken else P['WEAKEN']*(P['WEAKEN_DUR'] or 3))+((ni['d']*0.5) if ni and ni['heavy'] else 0)
    if ef=='Momentum': return top*0.9*(0.37 if P['MOM_FRAC']=='ceil3' else P['MOM_FRAC'])
    if ef=='Critical Hit': return top*P['CRIT']
    if ef=='Chain': return top*P['CHAIN_MULT'] if others else top*P['CHAIN_FALL']
    if ef=='Execute': return max([e.hp for e in ctx['all'] if 0<e.hp-(ctx['dmg'] if e is t else 0)<=max(P['EXEC'],P['EXECF']*e.max)] or [P['EXEC_FALL']])+2
    if ef=='Encore': return 10*P['ENCORE']
    if ef=='Meteor': return top*P.get('METEOR_MULT',4)*(1+len(others))
    if ef=='Time Stop': return 0              # happens inside the attack (simulated); see the effects loop
    if ef=='Overdrive': return ctx.get('sq',0)*P.get('OVERDRIVE',2)
    if ef=='Phoenix': return 0 if ctx.get('phx') else 12
    if ef=='Godslayer':
        if P.get('GODSLAYER','minion')=='minion':
            mn=[e for e in ctx['all'] if e.hp>0 and not e.boss and (P.get('GODSLAYER_MINI',1) or not getattr(e,'mini',False))]
            return max(e.hp for e in mn) if mn else P.get('GODSLAYER_DMG',25)
        nb=[e for e in ctx['all'] if e.hp>0 and not e.boss]
        if nb: return max(e.hp for e in nb)
        b=[e for e in ctx['all'] if e.hp>0 and e.boss]
        if not b: return 0
        b=b[0]; th=[t_ for t_ in (int(b.max*2/3),int(b.max/3)) if b.hp>t_]
        return (b.hp-th[0]) if th else b.hp//2
    if ef=='Echo': return ctx['dmg']+0.5*ctx['guard']            # this attack again, next turn
    return 0
def fight(enemies,strategy,offers,hero,phases=None,pattern_override=None,maxr=40,blank=()):
    SS=hero.get('STR',0); II=hero.get('INT',0); DD=hero.get('DEX',0)
    if P['POOL_SCOPE']=='scenario':
        hero.setdefault('rpool',int(P['DEX_REROLL']*DD)); hero.setdefault('ign',int(P['INT_IGNORE']*II)); rpool=hero['rpool']; ign=hero['ign']
    else:
        ign=P['INT_IGNORE']*II; rpool=int(P['DEX_REROLL']*DD)
    CLS=hero.get('cls'); BASE=BASEOF.get(CLS,CLS)
    if CLS=='Trickster':
        if P.get('T_SCOPE')=='scenario': hero.setdefault('trr',P['T_RR']); rpool+=hero['trr']; tr_start=rpool
        else: rpool+=P['T_RR']
    form=None
    if CLS=='Druid':
        isboss=any(e.boss for e in enemies); pol=P['D_POL']
        form={'bear':'bear','cat':'cat','bossbear':('bear' if isboss else 'cat'),'bosscat':('cat' if isboss else 'bear')}[pol]
    minions=(P['NC_START']+(P.get('NC_BOSSSTART',0) if any(e.boss for e in enemies) else 0)) if CLS=='Necromancer' else 0; carry=0; deadseen=set()
    hp=hero['hp']; maxhp=hero['max']; taken=0;r=0;gold=0;mark=0;momentum=0;big=0;maxhit=0;weakh=0;crits=0;counters=0
    LV=hero.get('lv') or {}; AB=set(LV.get('abil',()))                   # leveled hero: grid, path abilities
    rage=0; reserve_left='reserve' in AB; unstop_left='unstoppable' in AB; aura_left='aura' in AB; last_rl=None
    oath=(('wrath' if hp>25 else 'mercy') if 'oath' in AB else None)
    RARS=SQ_RAR; REM=P['REMOVED']
    echo_next=None; charge_next=True; charged=False
    HOLD=P.get('HOLD_MODE','bulwark2'); keep_next=0; shield_round=False; counter_round=False
    RCOST=P.get('RAGE_COST') or (2 if 'rage2' in AB else 3)            # Rage: a re-roll costs 3 boxes (2 from level 4)
    pend_mode=None; ppois=[]; used={}; gold_lost=0
    bossE=next((e for e in enemies if e.boss),None)
    while any(e.hp>0 for e in enemies) and r<maxr:
        r+=1; alive=[e for e in enemies if e.hp>0]
        if hero.get('potions',0)>0 and P.get('POT_THR') and hp<=P['POT_THR'] and hp<maxhp:
            if P.get('POT_MODE','low')=='low' or (P.get('POT_MODE')=='boss' and any(e.boss for e in enemies)):
                hero['potions']-=1; hp=min(maxhp,hp+P['POT_HEAL'])
        phase=('normal','')
        if bossE and bossE.hp>0 and phases:
            fr=bossE.hp/bossE.max; phase=phases[0] if fr>2/3 else (phases[1] if fr>1/3 else phases[2])
        press=phase[1] if isinstance(phase,tuple) else ''
        kp={}
        covers=[e for e in alive if e.cover]
        if covers: target=covers[0]
        else:
            pri=[e for e in alive if e.mode]; pool=pri if pri else [e for e in alive if not e.boss] or alive
            target=min(pool,key=lambda e:e.hp)
        # board mode
        mode='normal'; kbulk=[0]*9
        if P.get('KW'):
            import kwboard
            board=[]; tsc=list(getattr(target,'kwt',[]))
            for e_ in alive: board+=getattr(e_,'kwb',[])
            if bossE and bossE.hp>0 and isinstance(phase,list):
                for k_ in phase:
                    n_=kwboard.parse(k_)[0]
                    if n_ in KW_BOARD: board.append(k_)
                    elif n_ in KW_TARGET:
                        if target.boss: tsc.append(k_)
                    elif n_ in KW_PRESS: kp[n_]=k_
            if pend_mode: board.append(pend_mode)
            if LV and 'aura' in AB and P.get('AURA_ALL',1): board=[k_ for k_ in board if kwboard.parse(k_)[0] not in ('Daze','Pin')]
            if LV and 'claws' in AB and P.get('CLAWS_EXPOSE',1): board.append(f"Exposed {P.get('CLAWS_EXPOSE',1)}")
            hs=None; fury=False
            if LV:
                o_=[]
                if reserve_left: o_.append('reserve=1')
                if unstop_left: o_.append('unstop=1')
                if 'bloodlust' in AB and hp<=P.get('BLOOD_HP',18): o_.append('bloodlust=1')
                ch_=max(P.get('CHARGE_ROW',3) if ('charge' in AB and charge_next) else 0, keep_next if (HOLD=='entrench' and keep_next) else 0)
                charged=bool(ch_) and 'charge' in AB and charge_next
                if ch_: o_+=[f'charge={ch_}']+(['chargex=1'] if ('charge' in AB and P.get('CHARGE_EXTRA',1)) else [])+([f"lance2={P.get('TRAMPLE_LANCE',2)}"] if ('trample' in AB and P.get('TRAMPLE_LANCE',2)) else [])
                if HOLD=='entrench2' and keep_next and not ch_: o_.append(f'head={keep_next[0]}:{keep_next[1]}')
                if 'hold' in AB and HOLD not in ('bulwark','bulwark2'):
                    o_.append('stop=1')
                    if HOLD in ('double','counter'): o_+=['stopguardx=1']+(['stopguard=1'] if 'hold2' in AB else [])
                    elif HOLD=='shield':
                        inc_=sum(e_.nxt()['d'] for e_ in alive if e_.nxt()); o_.append(f'stopval={2*round(0.2*inc_)}')
                    elif HOLD=='entrench': o_.append('stopkeep=1')
                    elif HOLD=='entrench2': o_.append(f"stopkeep={P.get('KEEP_W',0.35)}")
                if 'pack' in AB:
                    pm_=P.get('PACK_MODE','with')      # free: Surge/weak steps, x2 | wild: wilds + steps, x2 | plus: wilds + steps, +1 | wildonly: wilds, x2
                    o_+=(['pack=1','packwild=0','packfree=0','packwith=1']+(['pack12=1'] if P.get('PACK_12') else [])+(['packcap=1'] if P.get('PACK_CAP',1) else [])+([f"packmax={P['PACK_MAX']}"] if P.get('PACK_MAX') else [])+(['packonce=1'] if P.get('PACK_ONCE') else [])+(['packnorm=1'] if P.get('PACK_DMG')=='normal' else ['packplus=1'] if P.get('PACK_DMG')=='plus' else []) if pm_=='with' else ['pack=1']+(['packwild=0'] if pm_=='free' and not P.get('PACK_WILD') else [])+(['packplus=1'] if pm_=='plus' else [])+(['packfree=0'] if pm_=='wildonly' else []))
                if 'Time Stop' in offers.get('M',()): o_+=[f"timestop={P.get('TS_MODE',2)}"]+([f"tsplus={P['TS_PLUS']}"] if P.get('TS_PLUS') else [])     # used on the first Mythic square reached
                fury=('fury' in AB and rage>=3 and hp<=P.get('FURY_HP',20))   # full Rage: re-roll, or (when low on HP) unleash on a fumble
                hs=dict(H=LV['H'],fat=LV.get('fat',4),wsteps=(P.get('CLAWS_STEPS',4) if 'claws' in AB else LV.get('wsteps',2)),wcolm=LV.get('wcolm',2),
                        rr=((rage//RCOST) if ('rage' in AB and not fury) else 0),hb2=LV.get('hb2',False),opts=o_)
                RARS=kwboard.hero_rarities(LV['H']); REM=set()
            mode,kd_,kbulk=kwboard.mode_for(board+tsc,hero.get('runners',3),hs); DMGT[mode]=kd_
        elif target.boss and phase[0] in ('exposed','cracked'): mode=('exposed2' if phase[0]=='exposed' else 'cracked')
        elif target.profile: mode=target.profile
        else:
            ms={e.mode for e in alive if e.mode}
            if bossE and bossE.hp>0 and phase[0] in TWISTS and phase[0] not in ('thickhide','plate'): ms.add(phase[0])
            if target.boss and phase[0] in ('thickhide','plate'): ms={phase[0]}
            if pend_mode: ms.add(pend_mode)
            for strong in ('pin','jinx','plate','thickhide'):
                if strong in ms: mode=strong; break
            else:
                if 'daze' in ms and 'traps' in ms: mode='dazetraps'
                elif ms: mode=sorted(ms)[0]
        if not P.get('KW') and mode=='exposed' and pend_mode: mode=pend_mode
        if CLS=='Assassin' and P.get('A_LOWER') and mode=='normal': mode='exposed2'
        pend_mode=None
        def ival(e):
            if e.sleep: return None
            it=dict(e.nxt())
            if e.boss:
                if press=='doom' and it['heavy']: it['d']=int(round(it['d']*1.5))
                if press=='frenzy': it['d']=int(round(it['d']*1.5))
            fz=((kp.get('Frenzy') if e.boss else None) or getattr(e,'kwp',{}).get('Frenzy')) if P.get('KW') else None
            if fz and (it['heavy'] or 'H' not in fz.split()[1:]): it['d']=int(round(it['d']*1.5))
            if (e.disarm or e.cancel) and it['heavy']: it=dict(e.intents[0]); it['heavy']=False
            if e.disarm and P['DISARM_HALF']==1: it['d']=it['d']//2; it['onhit']=None
            if e.disarm and P['DISARM_HALF']==2: it['d']=max(0,it['d']-3); it['onhit']=None
            if e.disarm and P['DISARM_HALF']==3: it['onhit']=None
            if e.disarm and P['DISARM_HALF']==4: it['d']=max(0,it['d']-1); it['onhit']=None
            if getattr(e,'groggy',0) and not e.sleep: it['d']=it['d']//2
            it['d']=max(0,it['d']-e.weaken-getattr(e,'frost',0)); return it
        intents=[(e,ival(e)) for e in alive]
        hasteD=int(round(0.7*max([x['d'] for x in bossE.intents if not x['heavy']] or [0]))) if bossE else 0
        if 'Haste' in kp: hasteD=kwx(kp['Haste'],4)
        incoming=sum(i['d'] for e,i in intents if i)+(hasteD if bossE and bossE.hp>0 and (press=='haste' or 'Haste' in kp) else 0)
        onhit_pending=any(i and i['onhit'] for e,i in intents)
        if strategy=='Aggressive': st,aim='g0',False
        elif strategy=='Balanced': st,aim='g1',False
        elif strategy=='Turtle': st,aim='g2',False
        elif strategy=='Hunter': st,aim='g0',True
        else: st,aim=('g2' if (incoming>=P['TACT_T'] or onhit_pending) else 'g0'),True
        k_=key(mode,target.weak,aim,st)
        if rpool>0:
            arr=load(k_+'_r1'); a=arr[random.randrange(len(arr))]
            if a[19]>0: rpool-=1
        elif CLS=='Warlock' and P.get('WL_RR') and hp>P['WL_MIN'] and used.get('_wl',0)<P.get('WL_CAP',99):
            arr=load(k_+'_r1'); a=arr[random.randrange(len(arr))]
            if a[19]>0: hp-=P['WL_COST']; taken+=P['WL_COST']; used['_wl']=used.get('_wl',0)+1
        else:
            arr=load(k_); a=arr[random.randrange(len(arr))]
        dmg,guard,fum,weak,top,mask=int(a[0]),int(a[1]),int(a[2]),int(a[3]),int(a[8]),int(a[9])
        ext=len(a)>20; ucount=int(a[22]) if ext else 0
        if LV and ext:
            if a[23]: reserve_left=False
            if ucount: unstop_left=False
            if 'rage' in AB: rage=min(3,max(0,rage-int(a[19])*RCOST)+fum+ucount)
            stp=bool(a[20]) and 'hold' in AB
            keep_next=(int(a[25]),int(a[24])) if (stp and HOLD=='entrench2' and len(a)>25 and a[24]>0) else (int(a[24]) if (stp and HOLD=='entrench' and len(a)>24) else 0)
            shield_round=stp and HOLD=='shield'; counter_round=stp and HOLD=='counter'
        weakh+=weak==1; crits+=weak==2
        if P.get('M_INS') and BASEOF.get(hero.get('cls'),hero.get('cls'))=='Mage' and weak==0 and int(a[1])>=P['M_INS']: weakh+=1
        cls=CLS; hh=a[10:19]; mana=int(a[1])
        if BASE=='Warrior': dmg+=int(round(P['W_OUTER']*sum(hh[c] for c in (0,8) if kbulk[c]<3)))
        if (BASE=='Rogue' or (CLS=='Druid' and form=='cat')) and weak==1:
            c0,r0=WEAKP[target.weak] if mode!='exposed2' else (WEAKP[target.weak][0],WEAKP[target.weak][1]-2)
            mult=P['D_CAT'] if CLS=='Druid' else P['R_WEAK']
            dmg+=int(mult*sum(coldmg(hh,c,mode) for c in {c0,8-c0} if hh[c]>=r0))
        if BASE=='Mage' and not (P.get('M_FIZZLE') and fum): dmg+=P.get('M_PLUS',0)
        if BASE=='Mage' and not (P.get('M_FIZZLE') and fum): dmg+=((mana+1)//2 if P['M_SPELL']=='half_up' else (mana+2)//3 if P['M_SPELL']=='third_up' else (mana+3)//4 if P['M_SPELL']=='quarter_up' else mana//4 if P['M_SPELL']=='quarter' else max(0,int(round(P['M_SPELL']*mana))-P.get('M_OFF',0)))
        if BASE=='Cleric':
            if P['C_DIV'] and not (P.get('C_ONCE') and used.get('_cheal')) and mana>=P.get('C_MIN',0):
                hp=min(maxhp,hp+min(P.get('C_CAP',99),mana//P['C_DIV'])); used['_cheal']=1
            if CLS=='Inquisitor': dmg+=mana//P['IQ_DIV']
            else: dmg+=(mana//4 if P['C_SMITE']=='per4' else mana//6 if P['C_SMITE']=='per6' else mana//5 if P['C_SMITE']=='per5' else int(round(P['C_SMITE']*mana)))
        if CLS=='Paladin' and not used.get('_pheal') and P['PA_HEAL']: hp=min(maxhp,hp+P['PA_HEAL']); used['_pheal']=1
        if CLS=='Barbarian':
            dm=DMGT.get(mode,[2,1,1,0,0,0,1,1,2]); dmg+=P['B_ABOVE']*sum(max(0,hh[c]-3) for c in range(9) if dm[c]>0)
        if CLS=='Assassin': dmg+=(P['A_WEAK'] if weak==1 else P['A_CRIT'] if weak==2 else 0)+(int(P.get('A_WMULT',0)*int(a[0])) if weak==1 else 0)
        if CLS=='Trickster': dmg+=(P.get('T_ALT',0) if r%2==0 else 0)
        if CLS=='Ranger': dmg+=P['RG_PET']+(P.get('RG_ALT',0) if r%2==0 else 0)
        if CLS=='Elementalist':
            mid=[hh[3],hh[4],hh[5]]; el=mid.index(max(mid)) if max(mid)>=P.get('E_MIN',1) else -1
            if el==0 and P['E_FIRE']: target.poison.append([P['E_FIRE'],2])
            elif el==1: dmg+=P['E_ARC']
            elif el==2:
                for e_ in enemies: e_.frost=P['E_FROST']
        dmg+=P.get('ASC_DMG',0)
        dmg+=P.get('CL_FLAT',0)
        if P.get('X_WEAKEN') and r==1: target.weaken=max(target.weaken,P['X_WEAKEN'])
        if CLS=='Necromancer': dmg+=minions*P['NC_DMG']
        if CLS=='Warlock':
            dmg+=P.get('WL_DMG',0)
            if P.get('WL_HEX') and r>1: dmg+=P['WL_HEX']
            if P.get('WL_HEXW') and r==1: target.weaken=max(target.weaken,P['WL_HEXW'])
            if P.get('WL_BLOOD') and hp>P['WL_MIN']: hp-=P['WL_COST']; taken+=P['WL_COST']; dmg+=P['WL_BLOOD']
        if CLS=='Druid' and form=='cat': dmg+=int(P.get('D_CATOUT',0)*(hh[0]+hh[8]))
        dmg+=P['STR_DMG']*SS
        if weak==1: dmg+=P['INT_WEAK']*II
        elif weak==2: dmg+=2*P['INT_WEAK']*II
        guard=int(round(guard*(P['D_BEAR'] if (CLS=='Druid' and form=='bear') else P['M_GUARD'] if BASE=='Mage' else P.get('C_GUARD',P['GUARD_MULT']) if BASE=='Cleric' else P.get('PA_GUARD',P['GUARD_MULT']) if CLS=='Paladin' else P['GUARD_MULT'])))+P['STR_GUARD']*SS+(P.get('W_GUARD',0) if BASE=='Warrior' else 0)+carry+(minions*P.get('NC_GUARD',0) if CLS=='Necromancer' else 0)+(P.get('CL_GUARD',0) if BASE=='Cleric' else 0)+(P.get('R_GUARD',0) if BASE=='Rogue' else 0)-(P.get('M_GMINUS',0) if BASE=='Mage' else 0); guard=max(0,guard); guard=min(guard,P['M_GCAP']) if (BASE=='Mage' and P.get('M_GCAP')) else guard; TRACE.append((CLS,guard)) if TRACE_ON else None; carry=0; dmg+=mark+momentum; mark=0; momentum=0
        if LV and ext and 'hold' in AB and a[20] and HOLD=='double': guard=guard*2+(int(a[21]) if 'hold2' in AB else 0)   # Hold the Line
        if echo_next: dmg+=echo_next[0]; guard+=echo_next[1]; echo_next=None   # Echo: last turn's attack happens again
        ts_pending=bool(LV and len(a)>26 and a[26]>0); echo_flag=False
        extra=[]; execute=False; encore=False; timestop=bool(LV and charged and P.get('CHARGE_STUN',1)); godslayer=False   # Charge knockback
        others=[e for e in alive if e is not target]
        fired=set(); brace_ctr=False
        for sq in bits(mask):
            rar=RARS[sq] if sq<len(RARS) else 'C'
            if rar in blank or sq in REM: continue
            opts=[o for o in offers.get(rar,[]) if not (o in P['ONCE'] and o in fired)]
            if rar=='M' and ts_pending and 'Time Stop' in opts: opts=['Time Stop']; ts_pending=False   # it fired on this square
            elif rar=='M': opts=[o for o in opts if o!='Time Stop'] or opts
            if not opts: continue
            ctx=dict(target=target,top=top,others=others,incoming=incoming,guard=guard,dmg=dmg,hp=hp,maxhp=maxhp,tnext=ival(target),all=enemies,
                     sq=int(sum(hh)),phx=hero.get('phoenix') or hero.get('phoenix_used'),last=last_rl)
            ef=max(opts,key=lambda o:effect_value(o,ctx)); used[ef]=used.get(ef,0)+1; fired.add(ef)
            if rar in ('R','L'): last_rl=ef
            if ef=='Meteor': mm_=top*P.get('METEOR_MULT',4); dmg+=mm_; extra.append(('meteor',mm_))
            elif ef=='Time Stop': timestop=bool(P.get('TS_SKIP',1))               # frozen rolls are in the attack; enemies may freeze too
            elif ef=='Echo': echo_flag=True
            elif ef=='Overdrive': dmg+=int(sum(hh))*P.get('OVERDRIVE',2)
            elif ef=='Phoenix': hero['phoenix']=0 if hero.get('phoenix_used') else 1
            elif ef=='Godslayer': godslayer=True
            elif ef=='Extra Attack': dmg+=1
            elif ef=='Brace':
                if P['BRACE_MODE']=='counter': brace_ctr=True
                elif P['BRACE_MODE']=='heavy':
                    if any(i and i['heavy'] for e_,i in intents): guard+=P['BRACE_HEAVY']
                else: guard+=P['BRACE']
            elif ef=='Mark': mark+=P['MARK']
            elif ef=='Poison I': target.poison.append(list(P['P1']))
            elif ef=='Poison II': target.poison.append(list(P['P2']))
            elif ef=='Ranged': extra.append(('ranged',2))
            elif ef=='Pickpocket': gold+=top; dmg+=P['PICK_DMG']
            elif ef=='Cleave': extra.append(('cleave',top//P['CLEAVE_DIV']) if others else ('self',int(top/P['CLEAVE_DIV']*2*P['CLEAVE_FALL'])))
            elif ef=='Leech':
                if not (P['LEECH_ONCE'] and used.get('_leeched')):
                    heal=P['LEECH_FLAT'] if P['LEECH_FLAT'] else int(top/P['LEECH_DIV']); hp=min(maxhp,hp+heal); used['_leeched']=1
            elif ef=='Disarm': target.disarm=P['DISARM_TURNS']
            elif ef=='Sleep': target.sleep=P['SLEEP_TURNS']
            elif ef=='Weaken': target.weaken=max(target.weaken,P['WEAKEN']); target.cancel=P['WEAKEN_CANCEL'] or target.cancel; target.wdur=P['WEAKEN_DUR']
            elif ef=='Momentum': momentum+=(-(-top//3) if P['MOM_FRAC']=='ceil3' else int(round(top*P['MOM_FRAC'])))
            elif ef=='Critical Hit': dmg+=int(round(top*P['CRIT']))
            elif ef=='Chain': extra.append(('chain',int(top*P['CHAIN_MULT'])) if others else ('self',int(top*P['CHAIN_FALL'])))
            elif ef=='Execute': execute=True
            elif ef=='Encore': encore=True
        if encore and P['ENCORE_SAFE']: fum=0
        if encore:
            for _ in range(P['ENCORE']):
                b=arr[random.randrange(len(arr))]; dmg+=int(b[0])
                if P['ENCORE_BONUS']:
                    for sq in bits(int(b[9])):
                        if sq in REM or sq>=len(RARS): continue
                        if RARS[sq] in ('L','M') or RARS[sq] in blank: continue
                        ctx=dict(target=target,top=int(b[8]),others=others,incoming=incoming,guard=guard,dmg=dmg,hp=hp,maxhp=maxhp,tnext=ival(target),all=enemies)
                        if not offers.get(RARS[sq]): continue
                        ef2=max(offers[RARS[sq]],key=lambda o:effect_value(o,ctx))
                        if ef2=='Extra Attack': dmg+=1
                        elif ef2=='Brace': guard+=P['BRACE']
                        elif ef2=='Mark': mark+=P['MARK']
                        elif ef2 in ('Poison I','Poison II'): target.poison.append([1 if ef2=='Poison I' else 2,3])
                        elif ef2=='Ranged': extra.append(('ranged',2))
                        elif ef2=='Cleave': extra.append(('cleave',int(b[8])//2) if others else ('self',int(int(b[8])*P['CLEAVE_FALL'])))
                        elif ef2=='Leech': hp=min(maxhp,hp+int(b[8])//2)
                        elif ef2=='Disarm': target.disarm=1
                        elif ef2=='Sleep': target.sleep=1
                        elif ef2=='Weaken': target.weaken=max(target.weaken,P['WEAKEN']); target.cancel=1
                        elif ef2=='Momentum': momentum+=int(b[8])
        if target.boss and press=='fortify': dmg=max(0,dmg-3)
        fo=(kp.get('Fortify') if target.boss else None) or getattr(target,'kwp',{}).get('Fortify')
        if fo: dmg=max(0,dmg-kwx(fo,3))
        total=dmg; target.hp-=dmg
        if echo_flag: echo_next=(dmg,guard)
        if 'trample' in AB and target.hp<0:                                # Trample: overflow carries to another enemy
            ov=-target.hp; cand=[e for e in enemies if e.hp>0 and e is not target]
            if cand: o=min(cand,key=lambda e:e.hp); o.hp-=ov; total+=ov
        for kind,v in extra:
            if kind=='meteor':
                for o in [e for e in enemies if e.hp>0 and e is not target]: o.hp-=v; total+=v
                continue
            if kind=='self':
                if target.hp>0: target.hp-=v; total+=v
                continue
            cand=[e for e in enemies if e.hp>0 and e is not target]
            if kind=='cleave' and covers: cand=[e for e in cand if e.cover]
            if not cand and kind=='ranged':
                if target.hp>0: target.hp-=P['RANGED_FALL']; total+=P['RANGED_FALL']
                continue
            if cand and v>0: o=min(cand,key=lambda e:e.hp); o.hp-=v; total+=v
        if execute:
            c=[e for e in enemies if 0<e.hp<=max(P['EXEC'],P['EXECF']*e.max)]
            if c: x=max(c,key=lambda e:e.max); total+=x.hp; x.hp=0
            elif P['EXEC_FALL'] and target.hp>0: target.hp-=P['EXEC_FALL']; total+=P['EXEC_FALL']
        if godslayer and P.get('GODSLAYER','minion')=='minion':
            mn=[e for e in enemies if e.hp>0 and not e.boss and (P.get('GODSLAYER_MINI',1) or not getattr(e,'mini',False))]
            if mn: x=max(mn,key=lambda e:e.hp); total+=x.hp; x.hp=0
            else:
                al_=[e for e in enemies if e.hp>0]
                if al_: x=target if target.hp>0 else min(al_,key=lambda e:e.hp); d_=min(x.hp,P.get('GODSLAYER_DMG',25)); x.hp-=d_; total+=d_
        elif godslayer:
            nb=[e for e in enemies if e.hp>0 and not e.boss]
            if nb: x=max(nb,key=lambda e:e.hp); total+=x.hp; x.hp=0
            elif bossE and bossE.hp>0:
                th=[t_ for t_ in (int(bossE.max*2/3),int(bossE.max/3)) if bossE.hp>t_]
                d_=(bossE.hp-th[0]) if th else bossE.hp//2; bossE.hp-=d_; total+=d_
        if CLS=='Necromancer':
            for e_ in enemies:
                if e_.hp<=0 and id(e_) not in deadseen: deadseen.add(id(e_)); minions=min(P['NC_CAP'],minions+1)
        big+=total>=25; maxhit=max(maxhit,total)
        charge_next=bool(P.get('CHARGE_EVERY')) or any(e_.hp<=0 for e_ in alive) or bool(P.get('CHARGE_N',3) and r%P.get('CHARGE_N',3)==0)   # wheel around every Nth attack
        if not any(e.hp>0 for e in enemies): break
        if fum and not brace_ctr and ign>0 and any(e.hp>0 for e in enemies): ign-=1; fum=0
        if fum and not brace_ctr:
            bz=(kwx(kp['Berserk'],2) if ('Berserk' in kp and bossE and bossE.hp>0) else 0)+max([kwx(e_.kwp['Berserk'],2) for e_ in enemies if e_.hp>0 and 'Berserk' in getattr(e_,'kwp',{})] or [0])
            c=max(0,(P['COUNTER']+2 if press=='berserk' and bossE and bossE.hp>0 else P['COUNTER'])+bz-P['INT_COUNTER']*II)*(1 if CLS!='Barbarian' else 1)+(P.get('B_CTRADD',0) if CLS=='Barbarian' else 0)
            if LV and fury:
                al_=[e for e in enemies if e.hp>0]
                if al_: (target if target.hp>0 else min(al_,key=lambda e:e.hp)).hp-=c
                if P.get('FURY_EMPTY',1): rage=0                                # unleashed: the Rage empties
            else: hp-=c; taken+=c; counters+=c
        if LV and ucount:
            bz=max([kwx(e_.kwp['Berserk'],2) for e_ in enemies if e_.hp>0 and 'Berserk' in getattr(e_,'kwp',{})] or [0])
            c=P['COUNTER']+bz; hp-=c; taken+=c; counters+=c
        for e in enemies:
            if e.hp>0:
                for p_ in e.poison: e.hp-=p_[0]; p_[1]-=1
                e.poison=[p_ for p_ in e.poison if p_[1]>0]
        if BASE=='Cleric' and P.get('C_SG'):
            for e_ in enemies:
                if e_.hp>0 and e_ is not target: e_.hp-=P['C_SG']
        if not any(e.hp>0 for e in enemies): break
        # player poison
        for p_ in ppois: hp-=p_[0]; taken+=p_[0]; p_[1]-=1
        ppois=[p_ for p_ in ppois if p_[1]>0]
        # enemies attack: guard pool
        g=guard; t=0
        for e in ([] if timestop else [e for e in enemies if e.hp>0]):
            it=ival(e); e.groggy=0 if not e.sleep else getattr(e,'groggy',0); e.i+=1; (setattr(e,'groggy',1) if (P['SLEEP_GROGGY'] and e.sleep==1) else None); e.sleep=max(0,e.sleep-1); e.disarm=max(0,e.disarm-1)
            if getattr(e,'wdur',0):
                e.wdur-=1
                if e.wdur==0: e.weaken=0
            e.frost=0
            if it is None: continue
            if BASE=='Cleric' and P.get('C_SANCT') and not used.get('_sanct') and it['d']>0: used['_sanct']=1; continue
            if P['DEX_EVADE'] and random.random()<P['DEX_EVADE']*DD: continue
            if it['heavy'] and e.cancel: e.cancel=0
            if P['DEX_ARMOR'] and DD: it=dict(it); it['d']=max(0,it['d']-P['DEX_ARMOR']*DD)
            if P['DEX_HALF'] and DD and random.random()<P['DEX_HALF']*DD: it=dict(it); it['d']=it['d']//2
            if P.get('R_EVADE') and BASE=='Rogue' and random.random()<P['R_EVADE']: it=dict(it); it['d']=(max(0,it['d']-P['R_EVFLAT']-(1 if (P.get('R_EVSPLIT') and random.random()<0.5) else 0)) if P.get('R_EVFLAT') else it['d']//2)
            eff_g=int(g*(1-it['pierce'])); through=max(0,it['d']-eff_g); g=max(0,g-(it['d']-through)) if it['pierce']==0 else g-min(g,it['d'])
            if shield_round: through//=2                                   # Shield wall: what gets past guard is halved
            t+=through
            if LV and 'seething' in AB and it['heavy'] and through>0: rage=min(3,rage+1)   # Seething: pain feeds Rage
            if through>0 and it['onhit'] and aura_left and it['onhit'] in ('poison','daze','pin','Daze','Pin'): aura_left=bool(P.get('AURA_ALL',1)); continue
            if through>0 and it['onhit'] and not (P['INT_RESIST'] and random.random()<P['INT_RESIST']*II):
                if it['onhit']=='poison': ppois.append([2,3])
                else: pend_mode=({'daze':'Daze','pin':'Pin'}.get(it['onhit'],it['onhit']) if P.get('KW') else it['onhit'])
            if P.get('KW') and through>0 and getattr(e,'thief',0): gold_lost+=e.thief
        if bossE and bossE.hp>0:
            if (press=='haste' or 'Haste' in kp) and not timestop: hh=max(0,hasteD-g); t+=hh
            if press=='regen': bossE.hp=min(bossE.max,bossE.hp+4)
            if 'Regen' in kp: bossE.hp=min(bossE.max,bossE.hp+kwx(kp['Regen'],4))
        for e_ in enemies:
            if e_.hp>0 and 'Regen' in getattr(e_,'kwp',{}): e_.hp=min(e_.max,e_.hp+kwx(e_.kwp['Regen'],4))
        hp-=t; taken+=t
        if CLS=='Knight': carry=int(g*P['K_CARRY'])
        if LV and 'hold' in AB and HOLD=='bulwark': carry=g//2              # Bulwark: half of leftover guard carries over
        bw_carry=False
        if LV and 'hold' in AB and HOLD=='bulwark2' and g>0:               # Bulwark (a choice): Riposte, or carry half the guard
            al_=[e_ for e_ in enemies if e_.hp>0]; ni_=sum(e_.nxt()['d'] for e_ in al_ if e_.nxt())
            if ni_>=P.get('BW_T',10) or any(e_.nxt() and e_.nxt()['heavy'] for e_ in al_): carry=g//(1 if 'hold2' in AB else P.get('BW_DIV',2)); bw_carry=True
        if bw_carry: pass
        elif counter_round and g>0:                                          # Counterattack: 1 per 2 leftover guard, no cap
            al=[e for e in enemies if e.hp>0]
            if al: tg=target if target.hp>0 else min(al,key=lambda e:e.hp); tg.hp-=g//2
        elif oath and g>0 and 'aura' in AB and P.get('AURA_BOTH',1):          # Radiant Aura: the Oath both damages and heals
            al=[e for e in enemies if e.hp>0]; amt=min(P.get('AURA_CAP',4),g//P.get('AURA_DIV',4))
            if al: tg=target if target.hp>0 else min(al,key=lambda e:e.hp); tg.hp-=amt
            hp=min(maxhp,hp+amt)
        elif oath and g>0:
            if oath=='wrath':
                al=[e for e in enemies if e.hp>0]
                if al: tg=target if target.hp>0 else min(al,key=lambda e:e.hp); tg.hp-=min(P.get('OATH_CAP',5),g//P.get('OATH_DIV',3))
            else: hp=min(maxhp,hp+min(P.get('OATH_CAP',5),g//P.get('OATH_DIV',3)))
        elif CLS=='Paladin' and g>0:
            al=[e for e in enemies if e.hp>0]
            if al: tg=target if target.hp>0 else min(al,key=lambda e:e.hp); tg.hp-=g//P['PA_DIV']
        elif P['RIPOSTE'] and g>0:
            al=[e for e in enemies if e.hp>0]
            if al: tg=target if target.hp>0 else min(al,key=lambda e:e.hp); tg.hp-=min(P.get('W_RIPCAP',P['RIP_CAP']) if BASE=='Warrior' else P['RIP_CAP'],g//P['RIPOSTE'])
        if hp<=0 and hero.get('phoenix'): hero['phoenix']=0; hero['phoenix_used']=1; hp=P.get('PHOENIX_HP',10)
        if hp<=0 and BASE=='Cleric' and P.get('C_DI') and not hero.get('_di'):
            hero['_di']=1
            if random.random()<P.get('C_DI_P',1.0): hp=P['C_DI']
        if hp<=0:
            hero['rpool']=rpool; hero['ign']=ign
            return dict(win=False,rounds=r,taken=taken,hp=hp,big=big,maxhit=maxhit,gold=gold,gold_lost=gold_lost,weak=weakh,crit=crits,counter=counters,used=used)
    if CLS=='Trickster' and P.get('T_SCOPE')=='scenario': hero['trr']=max(0,rpool)
    hero['rpool']=rpool; hero['ign']=ign
    return dict(win=not any(e.hp>0 for e in enemies),rounds=r,taken=taken,hp=hp,big=big,maxhit=maxhit,gold=gold,gold_lost=gold_lost,weak=weakh,crit=crits,counter=counters,used=used,stall=r>=maxr)
