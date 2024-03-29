# !/usr/bin/env python

""" tauFun.py: apply selection sequence to four-lepton final state """

import io
import yaml
import subprocess
from ROOT import TLorentzVector
from math import sqrt, sin, cos, pi

__author__ = "Dan Marlow, Alexis Kalogeropoulos, Gage DeZoort"
__date__   = "Monday, Oct. 28th, 2019"

# get selections from configZH.yaml:
with io.open('configZH_tight.yaml', 'r') as stream:
    selections = yaml.load(stream)
print "Using selections:\n", selections


def getTauList(channel, entry, pairList=[]) :
    """ tauFun.getTauList(): return a list of taus that 
                             pass the basic selection cuts               
    """

    if not channel in ['mmtt','eett'] :
        print("Warning: invalid channel={0:s} in tauFun.getTauList()".format(channel))
        exit()

    if entry.nTau == 0: return []

    tauList = []
    tt = selections['tt'] # selections for H->tau(h)+tau(h)
    for j in range(entry.nTau):    

        # apply tau(h) selections 
        if entry.Tau_pt[j] < tt['tau_pt']: continue
        if abs(entry.Tau_eta[j]) > tt['tau_eta']: continue
        if ord(entry.Tau_idAntiMu[j]) <= tt['tau_antiMu']: continue
        if ord(entry.Tau_idAntiEle[j]) <= tt['tau_antiEle']: continue
        if not entry.Tau_idDecayMode[j]: continue
        if abs(entry.Tau_dz[j]) > tt['tau_dz']: continue
        if not 0.5 < abs(entry.Tau_charge[j]) < 1.5: continue
        eta, phi = entry.Tau_eta[j], entry.Tau_phi[j]
        DR0, DR1 =  lTauDR(eta,phi, pairList[0]), lTauDR(eta,phi,pairList[1]) 
        if DR0 < tt['lt_DR'] or DR1 < tt['lt_DR']: continue
        tauList.append(j)
    
    return tauList


def tauDR(entry, j1,j2) :
    if j1 == j2 : return 0. 
    phi1, eta1, phi2, eta2 = entry.Tau_phi[j1], entry.Tau_eta[j1], entry.Tau_phi[j2], entry.Tau_eta[j2]
    return sqrt( (phi2-phi1)**2 + (eta2-eta1)**2 )


def lTauDR(eta1,phi1,Lep) :
    phi2, eta2 = Lep.Phi(), Lep.Eta()
    dPhi = min(abs(phi2-phi1),2.*pi-abs(phi2-phi1))
    return sqrt(dPhi**2 + (eta2-eta1)**2)


def DRobj(eta1,phi1,eta2,phi2) :
    dPhi = min(abs(phi2-phi1),2.*pi-abs(phi2-phi1))
    return sqrt(dPhi**2 + (eta2-eta1)**2)


def getTauPointer(entry, eta1, phi1) :
    # find the j value that most closely matches the specified eta or phi value
    bestMatch, jBest = 999., -1
    for j in range(entry.nTau) :
        eta2, phi2 = entry.Tau_eta[j], entry.Tau_phi[j]
        dPhi = min(abs(phi2-phi1),2.*pi-abs(phi2-phi1))
        DR = sqrt(dPhi**2 + (eta2-eta1)**2)
        if DR < bestMatch : bestMatch, jBest = DR, j
    if bestMatch > 0.1 :
        jBest = -1 
        print("Error in getTauPointer():   No match found eta={0:.3f} phi={1:.3f}".format(eta1,phi1))
    return jBest

        
def comparePair(entry, pair1, pair2) :
    """ tauFun.comparePair.py: return true if pair2 is 
                               better than pair1 
    """
    
    j1, j2 = pair1[0], pair2[0] # look at leading pt tau in each pair
    if entry.Tau_rawMVAoldDM2017v2[j2] < entry.Tau_rawMVAoldDM2017v2[j1] :
        return True
    elif  entry.Tau_rawMVAoldDM2017v2[j2] > entry.Tau_rawMVAoldDM2017v2[j1] :
        return False
    elif entry.Tau_pt[j2] > entry.Tau_pt[j1] :
        return True
    elif entry.Tau_pt[j2] < entry.Tau_pt[j1] :
        return False

    j1, j2 = pair1[1], pair2[1] # look at trailing pt tau in each pair
    if entry.Tau_rawMVAoldDM2017v2[j2] < entry.Tau_rawMVAoldDM2017v2[j1] :
        return True
    elif  entry.Tau_rawMVAoldDM2017v2[j2] > entry.Tau_rawMVAoldDM2017v2[j1] :
        return False
    elif entry.Tau_pt[j2] > entry.Tau_pt[j1] :
        return True
    else : 
        return False


def getBestTauPair(channel, entry, tauList) :
    """ tauFun.getBestTauPair(): return two taus that 
                                 best represent H->tt
    """ 

    if not channel in ['mmtt','eett'] : 
        print("Invalid channel={0:s} in tauFun.getBestTauPair()".format(channel))
        exit()

    if len(tauList) < 2: return [] 
    
    # form all possible pairs that satisfy DR requirement
    tauPairList = []
    tt = selections['tt'] # selections for H->(tau_h)(tau_h)
    for i in range(len(tauList)) :
        idx_tau1 = tauList[i]
        for j in range(len(tauList)) :
            if i == j: continue
            idx_tau2 = tauList[j]
            if tauDR(entry, idx_tau1, idx_tau2) < tt['tt_DR'] : continue
            tauPairList.append([idx_tau1, idx_tau2])

    # Sort the pair list using a bubble sort
    # The list is not fully sorted, since only the top pairing is needed
    for i in range(len(tauPairList)-1,0,-1) :
        if comparePair(entry, tauPairList[i],tauPairList[i-1]) : 
            tauPairList[i-1], tauPairList[i] = tauPairList[i], tauPairList[i-1] 

    if len(tauPairList) == 0 : return []
    idx_tau1, idx_tau2 = tauPairList[0][0], tauPairList[0][1]
    if entry.Tau_pt[idx_tau2] > entry.Tau_pt[idx_tau1] : 
        temp = tauPairList[0][0]
        tauPairList[0][0] = tauPairList[0][1]
        tauPairList[0][1] = temp
        
    return tauPairList[0]


def getMuTauPairs(entry,cat='mt',pairList=[],printOn=False) :
    """  tauFun.getMuTauPairs.py: return list of acceptable pairs
                                 of muons and taus 
    """

    if entry.nMuon < 1 or entry.nTau < 1: return []
    if cat == 'mmmt' and entry.nMuon < 3: return []

    muTauPairs = []
    mt = selections['mt'] # H->tau(mu)+tau(h) selections
    for i in range(entry.nMuon):
        
        # apply tau(mu) selections
        if mt['mu_ID']:
            if not entry.Muon_mediumId[i]: continue
        if abs(entry.Muon_dxy[i]) > mt['mu_dxy']: continue
        if abs(entry.Muon_dz[i]) > mt['mu_dz']: continue
        mu_eta, mu_phi = entry.Muon_eta[i], entry.Muon_phi[i] 
        if entry.Muon_pt[i] < mt['mu_pt']: continue
        if abs(mu_eta) > mt['mu_eta']: continue 
        DR0 = lTauDR(mu_eta,mu_phi,pairList[0]) # l1 vs. tau(mu)
        DR1 = lTauDR(mu_eta,mu_phi,pairList[1]) # l2 vs. tau(mu)
        if DR0 < mt['lt_DR'] or DR1 < mt['lt_DR']: continue
                        
        for j in range(entry.nTau):

            # apply tau(h) selections 
            if abs(entry.Tau_eta[j]) > mt['tau_eta']: continue
            if entry.Tau_pt[j] < mt['tau_pt']: continue
            if ord(entry.Tau_idAntiMu[j]) <= mt['tau_antiMu']: continue
            if ord(entry.Tau_idAntiEle[j]) <= mt['tau_antiEle']: continue
            if cat == 'eemt':
                if ord(entry.Tau_idAntiMu[j]) < mt['tau_eemt_antiMu']: continue
            if ord(entry.Tau_idMVAoldDM2017v2[j]) <= mt['tau_ID']: continue
            if abs(entry.Tau_dz[j]) > mt['tau_dz']: continue
            if mt['tau_decayMode']:
                if not entry.Tau_idDecayMode[j]: continue
            tau_eta, tau_phi = entry.Tau_eta[j], entry.Tau_phi[j]
            dPhi = min(abs(tau_phi-mu_phi),2.*pi-abs(tau_phi-mu_phi))
            DR = sqrt(dPhi**2 + (tau_eta-mu_eta)**2) # tau(mu) vs. tau(h)
            if DR < mt['mt_DR']: continue
            DR0 = lTauDR(tau_eta, tau_phi, pairList[0]) #l1 vs. tau(h)
            DR1 = lTauDR(tau_eta, tau_phi, pairList[1]) #l2 vs. tau(h)
            if DR0 < mt['lt_DR'] or DR1 < mt['lt_DR']: continue
            muTauPairs.append([i,j])

    return muTauPairs


def compareMuTauPair(entry,pair1,pair2) :
    # a return value of True means that pair2 is "better" than pair 1 
    i1, i2, j1, j2 = pair1[0], pair2[0], pair1[1], pair2[1]
    if entry.Muon_pfRelIso04_all[i2]  <  entry.Muon_pfRelIso04_all[i1] : return True
    if entry.Muon_pfRelIso04_all[i2] ==  entry.Muon_pfRelIso04_all[i1] :
        if entry.Muon_pt[i2] >  entry.Muon_pt[i1] : return True
        if entry.Muon_pt[i2] == entry.Muon_pt[i1] :
            if entry.Tau_rawMVAoldDM2017v2[j2] < entry.Tau_rawMVAoldDM2017v2[j1] : return True   
    return False


def getBestMuTauPair(entry,cat='mt',pairList=[],printOn=False) :

    # form all possible pairs that satisfy DR requirement
    tauPairList = getMuTauPairs(entry,cat=cat,pairList=pairList,printOn=printOn) 

    # Sort the pair list using a bubble sort
    # The list is not fully sorted, since only the top pairing is needed
    for i in range(len(tauPairList)-1,0,-1) :
        if compareMuTauPair(entry, tauPairList[i],tauPairList[i-1]) : 
            tauPairList[i-1], tauPairList[i] = tauPairList[i], tauPairList[i-1] 

    if len(tauPairList) == 0 : return []
    return tauPairList[0]


def getEMuTauPairs(entry,cat='em',pairList=[],printOn=False) :
    """ tauFun.getEMuTauPairs(): returns a list of suitable
                                 H-> tau(mu) + tau(ele) cands 
    """

    if entry.nMuon < 1 or entry.nElectron < 1: return []
    if cat == 'mmem' and entry.nMuon < 3:      return []
    if cat == 'eeem' and entry.nElectron < 3:  return []

    elmuTauPairs = []
    em = selections['em'] # selections for H->tau(ele)+tau(mu)
    for i in range(entry.nMuon):

        # selections for tau(mu)
        if em['mu_ID']:
            if not entry.Muon_mediumId[i]: continue
        if abs(entry.Muon_dxy[i]) > em['mu_dxy']: continue
        if abs(entry.Muon_dz[i]) > em['mu_dz']: continue
        mu_eta, mu_phi = entry.Muon_eta[i], entry.Muon_phi[i] 
        if entry.Muon_pt[i] < em['mu_pt']: continue
        if abs(mu_eta) > em['mu_eta']: continue   
        if em['mu_iso']:
            if entry.Muon_pfRelIso04_all[i] > 0.25: continue 
        
        DR0 = lTauDR(mu_eta,mu_phi,pairList[0]) #l1 vs. tau(mu)
        DR1 = lTauDR(mu_eta,mu_phi,pairList[1]) #l2 vs. tau(mu)
        if DR0 < em['lt_DR'] or DR1 < em['lt_DR']: continue
                        
        for j in range(entry.nElectron):
           
            # selections for tau(ele)
            if abs(entry.Electron_dxy[j]) > em['ele_dxy']: continue
            if abs(entry.Electron_dz[j]) > em['ele_dz']: continue
            ele_eta, ele_phi = entry.Electron_eta[j], entry.Electron_phi[j] 
            if entry.Electron_pt[j] < em['ele_pt']: continue
            if abs(ele_eta) > em['ele_eta']: continue
            if ord(entry.Electron_lostHits[j]) > em['ele_lostHits']: continue 
            if em['ele_convVeto']:
                if not entry.Electron_convVeto[j]: continue
            if em['ele_ID']:    
                if not entry.Electron_mvaFall17V2noIso_WP90[j]: continue
            if em['ele_iso']:
                if entry.Electron_pfRelIso03_all[j] > 0.5: continue

            dPhi = min(abs(mu_phi-ele_phi),2.*pi-abs(mu_phi-ele_phi))
            DR = sqrt(dPhi**2 + (mu_eta-ele_eta)**2) # tau(mu) vs. tau(ele)
            if DR < em['em_DR']: continue
            DR0 = lTauDR(ele_eta,ele_phi,pairList[0]) # l1 vs. tau(ele) 
            DR1 = lTauDR(ele_eta,ele_phi,pairList[1]) # l2 vs. tau(ele)
            if DR0 < em['lt_DR'] or DR1 < em['lt_DR']: continue
            elmuTauPairs.append([j,i])

    return elmuTauPairs


def compareEMuTauPair(entry,pair1,pair2) :
    # a return value of True means that pair2 is "better" than pair 1 
    i1, i2, j1, j2 = pair1[0], pair2[0], pair1[1], pair2[1]
    #if entry.Electron_mvaFall17Iso[i2]  < entry.Electron_mvaFall17Iso[i2] : return True
    if entry.Electron_mvaFall17V2Iso[i2]  < entry.Electron_mvaFall17V2Iso[i1] : return True
    #if entry.Electron_mvaFall17Iso[i2] == entry.Electron_mvaFall17Iso[i2] :
    if entry.Electron_mvaFall17V2Iso[i1] == entry.Electron_mvaFall17V2Iso[i2] : 
        if entry.Electron_pt[i2]  > entry.Electron_pt[i1] : return True 
        if entry.Electron_pt[i2] == entry.Electron_pt[i1] : 
            if entry.Muon_pt[j2] < entry.Muon_pt[j1] : return True   
    return False 


def getBestEMuTauPair(entry,cat,pairList=[],printOn=False) :

    if printOn : print("Entering getBestEMuTauPair")
    # form all possible pairs that satisfy DR requirement
    tauPairList = getEMuTauPairs(entry,cat=cat,pairList=pairList,printOn=printOn) 

    # Sort the pair list using a bubble sort
    # The list is not fully sorted, since only the top pairing is needed
    for i in range(len(tauPairList)-1,0,-1) :
        if compareEMuTauPair(entry, tauPairList[i],tauPairList[i-1]) : 
            tauPairList[i-1], tauPairList[i] = tauPairList[i], tauPairList[i-1] 

    if len(tauPairList) == 0 : return []
    return tauPairList[0]


def getETauPairs(entry,cat='et',pairList=[],printOn=False) :
    """ tauFun.getETauPairs(): get suitable pairs of 
                               H -> tau(ele) + tau(h) 
    """

    if entry.nElectron < 1 or entry.nTau < 1: return []
    if cat == 'eeet' and entry.nElectron < 3: return []
    
    eTauPairs = []
    et = selections['et'] # selections for H->tau(ele)+tau(h)
    for i in range(entry.nElectron) :

        # selections for tau(ele)
        if abs(entry.Electron_dxy[i]) > et['ele_dxy']: continue
        if abs(entry.Electron_dz[i]) > et['ele_dz']: continue
        if et['ele_ID']:
            if not entry.Electron_mvaFall17V2noIso_WP90[i]: continue
        if ord(entry.Electron_lostHits[i]) > et['ele_lostHits']: continue 
        if et['ele_convVeto']:
            if not entry.Electron_convVeto[i]: continue
        ele_eta, ele_phi = entry.Electron_eta[i], entry.Electron_phi[i]
        if entry.Electron_pt[i] < et['ele_pt']: continue
        if abs(ele_eta) > et['ele_eta']: continue
        DR0 = lTauDR(ele_eta,ele_phi,pairList[0]) # l1 vs. tau(ele)
        DR1 = lTauDR(ele_eta,ele_phi,pairList[1]) # l2 vs. tau(ele)
        if DR0 < et['lt_DR'] or DR1 < et['lt_DR']: continue
            
        for j in range(entry.nTau) :

            # selections for tau(h)
            if abs(entry.Tau_eta[j]) > et['tau_eta']: continue
            if entry.Tau_pt[j] < et['tau_pt']: continue
            if ord(entry.Tau_idAntiMu[j]) <= et['tau_antiMu']: continue
            if ord(entry.Tau_idAntiEle[j]) <= et['tau_antiEle']: continue
            if cat == 'eeet':
                if ord(entry.Tau_idAntiEle[j]) < et['tau_eeet_antiEle']: continue
            if ord(entry.Tau_idMVAoldDM2017v2[j]) <= et['tau_ID']: continue
            if et['tau_decayMode']:
                if not entry.Tau_idDecayMode[j]: continue
            if abs(entry.Tau_dz[j]) > et['tau_dz']: continue
            tau_eta, tau_phi = entry.Tau_eta[j], entry.Tau_phi[j]
            dPhi = min(abs(tau_phi-ele_phi),2.*pi-abs(tau_phi-ele_phi))
            DR = sqrt(dPhi**2 + (tau_eta-ele_eta)**2)
            if DR < et['tt_DR']: continue # tau(ele) vs. tau(h)
            DR0 = lTauDR(tau_eta,tau_phi,pairList[0]) # l1 vs. tau(h)
            DR1 = lTauDR(tau_eta,tau_phi,pairList[1]) # l2 vs. tau(h)
            if DR0 < et['lt_DR'] or DR1 < et['lt_DR']: continue
            if not 0.5 < abs(entry.Tau_charge[j]) < 1.5: continue
            eTauPairs.append([i,j])

    return eTauPairs

def compareETauPair(entry,pair1,pair2) :
    # a return value of True means that pair2 is "better" than pair 1 
    i1, i2, j1, j2 = pair1[0], pair2[0], pair1[1], pair2[1]
    #if entry.Electron_mvaFall17Iso[i2]  < entry.Electron_mvaFall17Iso[i2] : return True
    if entry.Electron_mvaFall17V2Iso[i2]  < entry.Electron_mvaFall17V2Iso[i1] : return True
    #if entry.Electron_mvaFall17Iso[i2] == entry.Electron_mvaFall17Iso[i2] :
    if entry.Electron_mvaFall17V2Iso[i1] == entry.Electron_mvaFall17V2Iso[i2] : 
        if entry.Electron_pt[i2]  > entry.Electron_pt[i1] : return True 
        if entry.Electron_pt[i2] == entry.Electron_pt[i1] : 
            if entry.Tau_rawMVAoldDM2017v2[j2] < entry.Tau_rawMVAoldDM2017v2[j1] : return True   
    return False 


def getBestETauPair(entry,cat,pairList=[],printOn=False) :

    if printOn : print("Entering getBestETauPair")
    # form all possible pairs that satisfy DR requirement
    tauPairList = getETauPairs(entry,cat=cat,pairList=pairList,printOn=printOn) 

    # Sort the pair list using a bubble sort
    # The list is not fully sorted, since only the top pairing is needed
    for i in range(len(tauPairList)-1,0,-1) :
        if compareETauPair(entry, tauPairList[i],tauPairList[i-1]) : 
            tauPairList[i-1], tauPairList[i] = tauPairList[i], tauPairList[i-1] 

    if len(tauPairList) == 0 : return []
    return tauPairList[0]


# select a muon for the Z candidate
def goodMuon(entry, j):
    """ tauFun.goodMuon(): select good muons
                           for Z -> mu + mu
    """
    
    mm = selections['mm'] # selections for Z->mumu
    if entry.Muon_pt[j] < mm['mu_pt']: return False
    if abs(entry.Muon_eta[j]) > mm['mu_eta']: return False
    if mm['mu_ID']:
        if not (entry.Muon_mediumId[j] or entry.Muon_tightId[j]): return False
    if entry.Muon_pfRelIso04_all[j] > mm['mu_iso']: return False
    if abs(entry.Muon_dxy[j]) > mm['mu_dxy']: return False 
    if abs(entry.Muon_dz[j]) > mm['mu_dz']: return False
    return True 

def makeGoodMuonList(entry) :
    goodMuonList = []
    for i in range(entry.nMuon) :
        if goodMuon(entry, i) : goodMuonList.append(i)
    #print("In tauFun.makeGoodMuonList = {0:s}".format(str(goodMuonList)))
    return goodMuonList

# select an electron for the Z candidate
def goodElectron(entry, j) :
    """ tauFun.goodElectron(): select good electrons 
                               for Z -> ele + ele
    """
    ee = selections['ee'] # selections for Z->ee
    if entry.Electron_pt[j] < ee['ele_pt']: return False
    if abs(entry.Electron_eta[j]) > ee['ele_eta']: return False
    if abs(entry.Electron_dxy[j]) > ee['ele_dxy']: return False
    if abs(entry.Electron_dz[j]) > ee['ele_dz']: return False
    if ord(entry.Electron_lostHits[j]) > ee['ele_lostHits']: return False
    if ee['ele_convVeto']:
        if not entry.Electron_convVeto[j]: return False
    #if not entry.Electron_mvaFall17Iso_WP90[j] : return False
    if ee['ele_ID']:
        if not entry.Electron_mvaFall17V2noIso_WP90[j] : return False
    return True 

def makeGoodElectronList(entry) :
    goodElectronList = []
    for i in range(entry.nElectron) :
        if goodElectron(entry, i) : goodElectronList.append(i)
    return goodElectronList

def eliminateCloseLeptons(entry, goodElectronList, goodMuonList) :
    badMuon, badElectron = [], []
    for mu1 in goodMuonList :
        for mu2 in goodMuonList :
            if mu1 == mu2 : continue
            dEta = abs(entry.Muon_eta[mu1] - entry.Muon_eta[mu2])
            if dEta > 0.3 : continue
            dPhi = abs(entry.Muon_phi[mu1] - entry.Muon_phi[mu2])
            if dPhi > 0.3 : continue
            if sqrt(dEta*dEta + dPhi*dPhi) > 0.3 : continue
            if not (mu1 in badMuon) : badMuon.append(mu1)
            if not (mu2 in badMuon) : badMuon.append(mu2)
        for e2 in goodElectronList :
            dEta = abs(entry.Muon_eta[mu1] - entry.Electron_eta[e2])
            if dEta > 0.3 : continue
            dPhi = abs(entry.Muon_phi[mu1] - entry.Electron_phi[e2])
            if dPhi > 0.3 : continue
            if sqrt(dEta*dEta + dPhi*dPhi) > 0.3 : continue
            if not (mu1 in badMuon) : badMuon.append(mu1)
            if not (e2 in badElectron) : badElectron.append(e2)
            
    for e1 in goodElectronList :
        for e2 in goodElectronList :
            if e1 == e2 : continue 
            dEta = abs(entry.Electron_eta[e1] - entry.Electron_eta[e2])
            if dEta > 0.3 : continue
            dPhi = abs(entry.Electron_phi[e1] - entry.Electron_phi[e2])
            if dPhi > 0.3 : continue
            if sqrt(dEta*dEta + dPhi*dPhi) > 0.3 : continue
            if not (e1 in badElectron) : badElectron.append(e1)
            if not (e2 in badElectron) : badElectron.append(e2)

    for bade in badElectron : goodElectronList.remove(bade)
    for badmu in badMuon : goodMuonList.remove(badmu)

    return goodElectronList, goodMuonList

def findETrigger(goodElectronList,entry,era):
    EltrigList =[]
    nElectron = len(goodElectronList)
    
    if nElectron > 1 :
	if era == '2016' and not entry.HLT_Ele27_WPTight_Gsf : return EltrigList
	if era == '2017' and not entry.HLT_Ele35_WPTight_Gsf : return EltrigList
        for i in range(nElectron) :
	    
            ii = goodElectronList[i]
            if era == '2016' and entry.Electron_pt[ii] < 29 : continue
            if era == '2017' and entry.Electron_pt[ii] < 37 : continue
            #print("Electron: pt={0:.1f} eta={1:.2f} phi={2:.2f}".format(entry.Electron_pt[ii], entry.Electron_eta[ii], entry.Electron_phi[ii]))
            #e1 = TLorentzVector()
            #e1.SetPtEtaPhiM(entry.Electron_pt[ii],entry.Electron_eta[ii],entry.Electron_phi[ii],0.0005)

            for iobj in range(0,entry.nTrigObj) :
	        dR = DRobj(entry.Electron_eta[ii],entry.Electron_phi[ii], entry.TrigObj_eta[iobj], entry.TrigObj_phi[iobj])
                #print("    Trg Obj: eta={0:.2f} phi={1:.2f} dR={2:.2f} bits={3:x}".format(
                    #entry.TrigObj_eta[iobj], entry.TrigObj_phi[iobj], dR, entry.TrigObj_filterBits[iobj]))
		if entry.TrigObj_filterBits[iobj] & 2  and dR < 0.5: ##that corresponds 0 WPTight
		    EltrigList.append(ii)
                    #print "======================= iobj", iobj, "entry_Trig",entry.TrigObj_id[iobj], "Bits", entry.TrigObj_filterBits[iobj]," dR", dR, "electron",i,"ii",ii,entry.TrigObj_id[iobj]

    return EltrigList


def findMuTrigger(goodMuonList,entry,era):
    MutrigList =[]
    nMuon = len(goodMuonList)
    
    if nMuon > 1 :
	if era == '2016' and not entry.HLT_IsoMu24 : return MutrigList
	if era == '2017' and not entry.HLT_IsoMu27 : return MutrigList
        for i in range(nMuon) :
	    

            ii = goodMuonList[i] 
	    if era == '2016' and entry.Muon_pt[ii] < 26 : continue
	    if era == '2017' and entry.Muon_pt[ii] < 29 : continue
            #print("Muon: pt={0:.1f} eta={1:.4f} phi={2:.4f}".format(entry.Muon_pt[ii], entry.Muon_eta[ii], entry.Muon_phi[ii]))
            for iobj in range(0,entry.nTrigObj) :
	        dR = DRobj(entry.Muon_eta[ii],entry.Muon_phi[ii], entry.TrigObj_eta[iobj], entry.TrigObj_phi[iobj])
                #print("    Trg Obj: eta={0:.4f} phi={1:.4f} dR={2:.4f} bits={3:x}".format(
                #    entry.TrigObj_eta[iobj], entry.TrigObj_phi[iobj], dR, entry.TrigObj_filterBits[iobj]))
		if entry.TrigObj_filterBits[iobj] & 8 or entry.TrigObj_filterBits[iobj] & 2 and dR < 0.5: ##that corresponds to Muon Trigger
		    MutrigList.append(ii)
                #print "======================= and === iobj", iobj, entry.TrigObj_id[iobj], "Bits", entry.TrigObj_filterBits[iobj]," dR", dR, "electron",i

    return MutrigList

def findZ(goodElectronList, goodMuonList, entry) :
    selpair,pairList, mZ, bestDiff = [],[], 91.19, 99999. 
    nElectron = len(goodElectronList)
    if nElectron > 1 :
        for i in range(nElectron) :
            ii = goodElectronList[i] 
            e1 = TLorentzVector()
            e1.SetPtEtaPhiM(entry.Electron_pt[ii],entry.Electron_eta[ii],entry.Electron_phi[ii],0.0005)
            for j in range(i+1,nElectron) :
                jj = goodElectronList[j]
                if entry.Electron_charge[ii] != entry.Electron_charge[jj] :
                    e2 = TLorentzVector()
                    e2.SetPtEtaPhiM(entry.Electron_pt[jj],entry.Electron_eta[jj],entry.Electron_phi[jj],0.0005)
                    cand = e1 + e2
                    mass = cand.M()
                    if abs(mass-mZ) < bestDiff :
                        bestDiff = abs(mass-mZ)
                        if entry.Electron_charge[ii] > 0. :
                            pairList = [e1,e2]
                            selpair = [ii,jj]
                        else : 
                            pairList = [e2,e1]
                            selpair = [jj,ii]
                            
    nMuon = len(goodMuonList)
    if nMuon > 1 : 
        # find mass pairings
        for i in range(nMuon) :
            ii = goodMuonList[i]
            mu1 = TLorentzVector()
            mu1.SetPtEtaPhiM(entry.Muon_pt[ii],entry.Muon_eta[ii],entry.Muon_phi[ii],0.105)
            for j in range(i+1,nMuon) :
                jj = goodMuonList[j]
                if entry.Muon_charge[ii] != entry.Muon_charge[jj] :
                    mu2 = TLorentzVector()
                    mu2.SetPtEtaPhiM(entry.Muon_pt[jj],entry.Muon_eta[jj],entry.Muon_phi[jj],0.105)
                    cand = mu1 + mu2
                    mass = cand.M()
                    if abs(mass-mZ) < bestDiff :
                        bestDiff = abs(mass-mZ)
                        if entry.Muon_charge[ii] > 0. :
                            pairList = [mu1,mu2]
                            selpair = [ii,jj]
                        else :
                            pairList = [mu2,mu1]
                            selpair = [jj,ii]

    # first particle of pair is positive
    #print selpair
    return pairList, selpair
                    
                    
def findZmumu(goodMuonList, entry) :
    pairList, mZ, bestDiff = [], 91.19, 99999.     
    nMuon = len(goodMuonList)
    if nMuon < 2 : return pairList 
    # find mass pairings
    for i in range(nMuon) :
        mu1 = TLorentzVector()
        mu1.SetPtEtaPhiM(entry.Muon_pt[i],entry.Muon_eta[i],entry.Muon_phi[i],0.105)
        for j in range(i+1,nMuon) :
            if entry.Muon_charge[i] != entry.Muon_charge[j] :
                mu2 = TLorentzVector()
                mu2.SetPtEtaPhiM(entry.Muon_pt[j],entry.Muon_eta[j],entry.Muon_phi[j],0.105)
                cand = mu1 + mu2
                mass = cand.M()
                if abs(mass-mZ) < bestDiff :
                    bestDiff = abs(mass-mZ)
                    pairList.append([mu1,mu2]) 

    return pairList

def findZee(goodElectronList, entry) :
    pairList, mZ, bestDiff = [], 91.19, 99999. 
    nElectron = len(goodElectronList)
    if nElectron < 2 : return pairList 
    # find mass pairings
    for i in range(nElectron) :
        e1 = TLorentzVector()
        e1.SetPtEtaPhiM(entry.Electron_pt[i],entry.Electron_eta[i],entry.Electron_phi[i],0.0005)
        for j in range(i+1,nElectron) :
            if entry.Electron_charge[i] != entry.Electron_charge[j] :
                e2 = TLorentzVector()
                e2.SetPtEtaPhiM(entry.Electron_pt[j],entry.Electron_eta[j],entry.Electron_phi[j],0.0005)
                cand = e1 + e2
                mass = cand.M()
                if abs(mass-mZ) < bestDiff :
                    bestDiff = abs(mass-mZ)
                    pairList.append([e1,e2]) 

    return pairList

def catToNumber(cat) :
    number = { 'eeet':1, 'eemt':2, 'eett':3, 'eeem':4, 'mmet':5, 'mmmt':6, 'mmtt':7, 'mmem':8, 'et':9, 'mt':10, 'tt':11 }
    return number[cat]

def numberToCat(number) :
    cat = { 1:'eeet', 2:'eemt', 3:'eett', 4:'eeem', 5:'mmet', 6:'mmmt', 7:'mmtt', 8:'mmem', 9:'et', 10:'mt', 11:'tt' }
    return cat[number]
    






    
    
    

    
