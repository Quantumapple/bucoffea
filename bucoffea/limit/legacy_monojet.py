#!/usr/bin/env python
import copy
import os
import re
from collections import defaultdict

import uproot
from coffea import hist
from coffea.hist.export import export1d

import ROOT as r
from bucoffea.plot.util import merge_datasets, merge_extensions, scale_xs_lumi

pjoin = os.path.join

def datasets(year, unblind=False):
    data = {
                    'cr_1m_j' : f'MET_{year}',
                    'cr_2m_j' : f'MET_{year}',
                    'cr_1e_j' : f'EGamma_{year}',
                    'cr_2e_j' : f'EGamma_{year}',
                    'cr_g_j' : f'EGamma_{year}',
                    'sr_j' : f'MET_{year}',
                    'sr_j_no_veto_all' : f'nomatch',
                }
    if unblind:
        data['sr_j'] = f'MET_{year}'

    tmp = {}
    for k, v in list(data.items()):
        tmp[k] = re.compile(v)
        k1=k.replace('_j','_v')
        tmp[k1] = re.compile(v)
    data.update(tmp)



    mc = {
            'cr_1m_j' : re.compile(f'(Top_FXFX|Diboson.*|QCD_HT.*|.*DYJetsToLL_M-50_HT_MLM.*|.*WJetsToLNu.*HT.*).*{year}'),
            'cr_1e_j' : re.compile(f'(Top_FXFX|Diboson.*|QCD_HT.*|.*DYJetsToLL_M-50_HT_MLM.*|.*WJetsToLNu.*HT.*|GJets_DR-0p4.*).*{year}'),
            'cr_2m_j' : re.compile(f'(Top_FXFX|Diboson.*|QCD_HT.*|.*DYJetsToLL_M-50_HT_MLM.*).*{year}'),
            'cr_2e_j' : re.compile(f'(Top_FXFX|Diboson.*|QCD_HT.*|.*DYJetsToLL_M-50_HT_MLM.*).*{year}'),
            'cr_g_j' : re.compile(f'(GJets_DR-0p4.*|QCD_data.*|WJetsToLNu.*HT.*).*{year}'),
            'sr_j_no_veto_all' : re.compile(f'(.*WJetsToLNu.*HT.*|.*ZJetsToNuNu.*HT.*|Top_FXFX.*|Diboson.*|QCD_HT.*|.*Hinv.*|.*HToInv.*).*{year}'),
            'sr_j' : re.compile('nomatch'),
            }
    for key in list(mc.keys()):
        new_key = key.replace('_j','_v')
        mc[new_key]=mc[key]
    return data, mc


def legacy_dataset_name(dataset):
    patterns = {
        '.*DY.*' : 'zll',
        'QCD.*' : 'qcd',
        '(Top).*' : 'top',
        'Diboson.*' : 'diboson',
        '(MET|EGamma).*' : 'data',
        'WJetsToLNu.*' : 'wjets',
        'ZJetsToNuNu.*' : 'zjets',
        'GJets_DR-0p4.*HT.*' : 'gjets',
        'WH.*Hinv.*' : 'wh',
        'ZH.*HToInvisible.*' : 'zh',
        'VBF.*HToInvisible.*' : 'vbf',
        'GluGlu.*HToInvisible.*' : 'ggh',
        'ggZH*HToInvisible.*' : 'ggzh',
    }

    for pat, ret in patterns.items():
        if re.match(pat, dataset):
            return ret
    raise RuntimeError(f'Cannot find legacy region name for dataset :"{dataset}"')

def legacy_region_name(region):
    patterns = {
        'cr_2m_.*' : 'Zmm',
        'cr_2e_.*' : 'Zee',
        'cr_1m_.*' : 'Wmn',
        'cr_1e_.*' : 'Wen',
        'cr_g_.*' : 'gjets',
        'sr_.*' : 'signal',
    }

    for pat, ret in patterns.items():
        if re.match(pat, region):
            return ret
    raise RuntimeError(f'Cannot find legacy region name for region :"{region}"')
def recoil_bins_2016():
    return [ 250.,  280.,  310.,  340.,  370.,  400.,
             430.,  470.,  510., 550.,  590.,  640.,
             690.,  740.,  790.,  840.,  900.,  960.,
             1020., 1090., 1160., 1250., 1400.]

def suppress_negative_bins(histogram):
    if "data" in histogram.GetName():
        return
    for i in range(0,histogram.GetNbinsX()+2):
        if histogram.GetBinContent(i) < 0:
            histogram.SetBinContent(i, 0)
            histogram.SetBinError(i,0)

def legacy_limit_input_monojet(acc, outdir='./output', unblind=False):
    """Writes ROOT TH1s to file as a limit input

    :param acc: Accumulator (processor output)
    :type acc: coffea.processor.accumulator
    :param outdir: Output directory
    :type outdir: string
    """
    distribution = 'recoil'

    regions = [
                'cr_2m_j',
                'cr_1m_j',
                'cr_2e_j',
                'cr_1e_j',
                'cr_g_j',
                'sr_j_no_veto_all'
                ]
    if unblind:
        regions.append('sr_j')

    if not os.path.exists(outdir):
        os.makedirs(outdir)

    for year in [2017,2018]:
        signal = re.compile(f'(GluGlu|WH|ZH|ggZH|VBF).*(I|i)inv.*{year}')
        f = uproot.recreate(pjoin(outdir, f'legacy_limit_monojet_{year}.root'))
        data, mc = datasets(year, unblind=unblind)

        for region in regions:
            print(f'Region {region}')
            # Rebin
            h = copy.deepcopy(acc[distribution])

            newax = hist.Bin('recoil','Recoil (GeV)', recoil_bins_2016())

            h = h.rebin(h.axis(newax.name), newax)

            h = merge_extensions(h, acc)
            scale_xs_lumi(h)

            h = merge_datasets(h)

            h = h.integrate(h.axis('region'),region)

            for dataset in map(str, h.axis('dataset').identifiers()):
                if not (data[region].match(dataset) or mc[region].match(dataset) or signal.match(dataset)):
                    continue
                print(f"   Dataset: {dataset}")

                th1 = export1d(h.integrate('dataset', dataset))
                try:
                    histo_name = f'{legacy_region_name(region)}_{legacy_dataset_name(dataset)}'
                except:
                    print(f"Skipping {dataset}")
                    continue
                f[histo_name] = th1

        if not unblind:
            f[f'{legacy_region_name("sr_j")}_data'] = f[f'{legacy_region_name("sr_j")}_zjets']
    merge_legacy_inputs(outdir)


def merge_legacy_inputs(outdir):
    '''
    Workaround for uproot's lack of subdirectory support.
    '''

    files = defaultdict(dict)
    for fname in os.listdir(outdir):
        m = re.match('legacy_limit_([a-z]*)_(\d+).root', fname)
        if not m:
            continue
        category, year = m.groups()
        files[year][category] = pjoin(outdir, fname)

    outfile = r.TFile(pjoin(outdir, f'legacy_limit_monojet.root'),'RECREATE')
    for year, ifiles in files.items():
        for category, file in ifiles.items():
            subdir = outfile.mkdir(f'category_{category}_{year}')
            infile = r.TFile(file)
            for key in infile.GetListOfKeys():
                print(key)
                h = key.ReadObj().Clone()
                h.SetTitle(h.GetName())
                h.SetDirectory(subdir)
                h.GetXaxis().SetTitle('met')
                suppress_negative_bins(h)
                # h.Write()
                subdir.Write()
