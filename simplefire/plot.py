"""
Plotting routines.
"""

import tempfile
from pathlib import Path
from typing import Optional
from functools import reduce
from operator import add

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib import rc
import svglue
import cairosvg

# enable latex
from simplefire.core import TaxEvasionStrategy
from simplefire.constants import _data_path
#
#
# class _TableBackgroundPlotter:
#     """An object for managing table background plots."""
#
#     def _clear_state(self):
#         """Clear any matplotlib state already in memeory."""
#         plt.cla()
#         plt.clf()
#
#     def center_text(self, x, y, text, fontsize=12, color='black', halign='center'):
#         """Plot centered text on axis"""
#         written = self.ax.text(
#             x,
#             y,
#             text,
#             horizontalalignment=halign,
#             verticalalignment='center',
#             transform=self.ax.transAxes,
#             fontsize=fontsize,
#             color=color,
#         )
#         return written
#
#     def _get_fig_ax(self):
#         """Init the figure and background plot"""
#         self._clear_state()
#         fig, ax = plt.subplots(1, 1, figsize=(11, 7))
#         ax.set_xlim(0, 1)
#         ax.set_ylim(0, 1)
#         ax.axis('off')
#         return fig, ax
#
#     def _make_labels(self):
#         """Plot labels on figure."""
#         self.center_text(0.5, 0.97, 'Income/Tax', fontsize=13)
#         # self.center_text(0.51, 0.9, 'Income Tax: ', halign='left')
#
#         left = 0.01
#         inv_top_start = 0.80
#
#         self.center_text(0.5, inv_top_start, 'Balance / Gains / Contributions')
#         self.center_text(left, inv_top_start - 0.1, 'TSP (Trad): ', halign='left')
#         self.center_text(left, inv_top_start - 0.2, 'Taxable: ', halign='left')
#         self.center_text(left, inv_top_start - 0.3, 'IRA (Roth): ', halign='left')
#         self.center_text(left, inv_top_start - 0.4, 'IRA (Traditional)', halign='left')
#
#         self.center_text(0.5, 0.3, 'Year-End Summary', fontsize=15)
#         self.center_text(0.5, 0.20, 'Invested / Gains / Spending')
#         plt.tight_layout()
#         plt.show()
#         breakpoint()
#
#     def __init__(self, year, income, spending, tsp, taxable, ira_roth, ira_trad):
#         self.fig, self.ax = self._get_fig_ax()
#         self._make_labels()


def plot_yearly_table(
        fire_strategy: TaxEvasionStrategy,
        plot_directory: Optional[Path] = None,
):
    """
    Make yearly table of fire strategy.
    """
    def _get_fig_ax(years):
        fig, ax =  plt.subplots(1, 1, figsize=(10, 7))
        ax.set_xlim(years.min(), years.max())
        return fig, ax

    output_dir = Path(plot_directory or tempfile.mkdtemp())
    income = fire_strategy.income_df
    household = fire_strategy.household_df
    emp = fire_strategy.employee_investment.df
    trad = fire_strategy.traditional_ira.df
    roth_df = fire_strategy.roth_ira.df
    taxable_df = fire_strategy.taxable.df
    trad_df = reduce(add, [emp, trad])

    total_df = reduce(add, [x.df for x in fire_strategy.investments])
    years = (total_df.index - total_df.index.min()) + 1
    with plt.xkcd():
        for num, year in enumerate(income.index):
            years_ = years[:num + 1]
            title = f"Year-{years_.max():02d}"
            fig, ax = _get_fig_ax(years)
            inc_array = income.loc[:year, 'income'].values / 1_000
            trad_array = trad_df.loc[:year, 'end_balance'].values / 1_000
            roth_array = roth_df.loc[:year, 'end_balance'].values / 1_000
            taxable_array = taxable_df.loc[:year, 'end_balance'].values / 1_000
            # plot time series
            ax.plot(years_, inc_array, label='income')
            ax.plot(years_, trad_array, label='traditional')
            ax.plot(years_, roth_array, label='roth')
            ax.plot(years_, taxable_array, label='taxable')
            max_y = np.max([inc_array.max(), trad_array.max(), roth_array.max(),
                          taxable_array.max()])
            # set lables and such
            ax.set_ylabel('1000 USD')
            ax.set_xlabel('year')
            ax.legend(loc=2)
            ax.set_title(title)
            ax.set_ylim(-10, max([max_y* 1.05, 400]))
            # label cumulative
            passive_income = int(total_df.loc[year, 'gains'] / 1_000)
            net_worth = int(total_df.loc[year, 'end_balance'] / 1_000)
            ax.text(0, 1.01, f'Net Worth: {net_worth} k', transform=ax.transAxes)
            ax.text(.75, 1.01, f"Passive Income: {passive_income} k", transform=ax.transAxes)
            # add retirement figure if retired
            # save figure
            path = plot_directory / f"{title}.png"
            path.parent.mkdir(exist_ok=True, parents=True)
            fig.savefig(path)