#!/usr/bin/env python
import argparse
import os
import re
import sys

from klepto.archives import dir_archive

from bucoffea.plot.stack_plot import make_plot
from bucoffea.plot.style import plot_settings
from bucoffea.plot.util import merge_datasets, merge_extensions, scale_xs_lumi


def plot(args):
        indir=os.path.abspath(args.inpath)

        # The processor output is stored in an
        # 'accumulator', which in our case is
        # just a dictionary holding all the histograms
        # Put all your *coffea files into 'indir' and
        # pass the directory as an argument here.
        # All input files in the direcotry will
        # automatically be found, merged and read.
        # The merging only happens the first time
        # you run over a specific set of inputs.
        acc = dir_archive(
                          args.inpath,
                          serialized=True,
                          compression=0,
                          memsize=1e3,
                          )

        # Get a settings dictionary that details
        # which plots to make for each region,
        # what the axis limits are, etc
        # Can add plots by extending the dictionary
        # Or modify axes ranges, etc
        settings = plot_settings()

        # For this check, I have two extra regions
        # that are not yet defined, but I want to
        # use the same settings as for an existing one
        # so I just copy them.
        settings['cr_2e_j_bare'] = settings['cr_2e_j']
        settings['cr_2e_j_vbare'] = settings['cr_2e_j']

        merged = set()
        # Separate plots per year
        for year in [2017, 2018]:
            # The data to be used for each region
            # Muon regions use MET,
            # electron+photon regions use EGamma
            # ( EGamma = SingleElectron+SinglePhoton for 2017)
            data = {
                'cr_1m_j' : f'MET_{year}',
                'cr_2m_j' : f'MET_{year}',
                'cr_1e_j' : f'EGamma_{year}',
                'cr_2e_j' : f'EGamma_{year}',
                'cr_g_j' : f'EGamma_{year}',
            }

            # Same for MC selection
            # Match datasets by regular expressions
            # Here for LO V samples (HT binned)
            mc_lo = {
                'cr_1m_j' : re.compile(f'(Top_FXFX.*|Diboson.*|QCD_HT.*|.*DYJetsToLL_M-50_HT_MLM.*|.*WJetsToLNu.*HT.*).*{year}'),
                'cr_1e_j' : re.compile(f'(Top_FXFX.*|Diboson.*|QCD_HT.*|.*DYJetsToLL_M-50_HT_MLM.*|.*WJetsToLNu.*HT.*|GJets_DR.*HT.*).*{year}'),
                'cr_2m_j' : re.compile(f'(Top_FXFX.*|Diboson.*|QCD_HT.*|.*DYJetsToLL_M-50_HT_MLM.*).*{year}'),
                'cr_2e_j' : re.compile(f'(Top_FXFX.*|Diboson.*|QCD_HT.*|DYJetsToLL_M-50_HT_MLM)_{year}'),
                'cr_g_j' : re.compile(f'(GJets_DR.*HT.*|QCD_data.*|WJetsToLNu.*HT.*).*{year}'),
            }

            # Load ingredients from cache
            acc.load('sumw')
            acc.load('sumw_pileup')
            acc.load('nevents')

            # Data / MC plots are made here
            # Loop over all regions
            for region in mc_lo.keys():
                if not re.match(args.region, region):
                        continue
                # Make separate output direcotry for each region
                outdir = f'./output/{os.path.basename(indir)}/{region}'

                # Settings for this region
                plotset = settings[region]

                # Loop over the distributions
                for distribution in plotset.keys():
                    if not re.match(args.distribution, distribution):
                        continue
                    # Load from cache
                    if not (distribution in merged):
                        acc.load(distribution)
                        if not (distribution in acc.keys()):
                            print(f"WARNING: Distribution {distribution} not found in input files.")
                            continue
                        acc[distribution] = merge_extensions(acc[distribution], acc, reweight_pu=not ('nopu' in distribution))
                        scale_xs_lumi(acc[distribution])
                        acc[distribution] = merge_datasets(acc[distribution])
                        acc[distribution].axis('dataset').sorting = 'integral'
                        merged.add(distribution)
                    try:
                        # The heavy lifting of making a plot is hidden
                        # in make_plot. We call it once using the LO MC

                        imc = mc_lo[region]
                        if "cr_g" in region and distribution!="recoil":
                            imc = re.compile(imc.pattern.replace('QCD_data','QCD.*HT'))
                        make_plot(acc,
                                region=region,
                                distribution=distribution,
                                year=year,
                                data=data[region],
                                mc=imc,
                                ylim=plotset[distribution].get('ylim',None),
                                xlim=plotset[distribution].get('xlim',None),
                                tag = 'losf',
                                outdir=f'./output/{os.path.basename(indir)}/{region}')

                    except KeyError:
                        continue
def commandline():
    parser = argparse.ArgumentParser(prog='Plotter.')
    parser.add_argument('inpath', type=str, help='Input folder to use.')
    parser.add_argument('--region', type=str, default='.*', help='Region to plot.')
    parser.add_argument('--distribution', type=str, default='.*', help='Distribution to plot.')
    args = parser.parse_args()
    return args

def main():
    args = commandline()
    plot(args)


if __name__ == "__main__":
    main()
