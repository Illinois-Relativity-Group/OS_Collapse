"""The user's direct memory projection, shared by the plot and movie inset."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from wave_eta import calc_Ylm

ROOT = Path(__file__).resolve().parent
MEMORY_COLOR = '#ff0000'


class MemoryComparison:
    def __init__(self, endpoint=286.9264112777602, wave_path=None, extraction_radius=112.):
        wave_path = Path(wave_path) if wave_path is not None else ROOT / 'hplus_1d.csv'
        memory_path = ROOT / 'memory_data.dat'
        wave = np.loadtxt(wave_path, delimiter=',', skiprows=1)
        memory = np.loadtxt(memory_path)
        if not np.isfinite(wave).all() or not np.isfinite(memory).all():
            raise ValueError('Nonfinite waveform or memory data')
        if np.any(np.diff(wave[:, 1]) <= 0) or np.any(np.diff(memory[:, 0]) <= 0):
            raise ValueError('Retarded times must increase')
        self.u, self.hp = wave[:, 1], wave[:, 2]
        self.mu = memory[:, 0]
        self.endpoint = endpoint
        if endpoint > min(self.u[-1], self.mu[-1]):
            raise ValueError('Comparison endpoint exceeds the supplied data')
        if extraction_radius <= 0:
            raise ValueError('Extraction radius must be positive')
        self.y20 = float(calc_Ylm(2, 0, np.pi/2, 0).real)
        self.physical = memory[:, -1] * .004**2 / extraction_radius * self.y20
        self.report = dict(
            method=f'Last memory column * 0.004**2 / {extraction_radius:g} * spin_minus_2_Y20(pi/2,0)',
            B0=.004, coordinate_radius=extraction_radius, equatorial_spin_minus_2_Y20=self.y20,
            memory_column='h_tot_20_mem/B_0^2 (last column)',
            waveform_column='hplus_1d.csv: hplus_unscaled',
            additional_fitting=False, time_shift=0, additive_baseline_shift=0,
            source_eta_modified=False, source_memory_modified=False, surface_modified=False,
            waveform_sha256=hashlib.sha256(wave_path.read_bytes()).hexdigest(),
            memory_sha256=hashlib.sha256(memory_path.read_bytes()).hexdigest(),
            waveform_path=str(wave_path.resolve()),
            normalization_assumption='Given memory times B0^2 is radius-weighted h20; not established by its header alone',
        )

    @classmethod
    def from_work(cls, work):
        work = Path(work)
        plan = json.loads((work/'plan.json').read_text())
        if 'wave_source' not in plan:
            return cls()
        model = cls(endpoint=plan['comparison_endpoint'], wave_path=work/'hplus_1d.csv',
                    extraction_radius=plan['wave_source']['r_ext'])
        if plan['wave_source'].get('format') == 'equatorial_radius_weighted':
            model.report['comparison_radius_role'] = 'Chosen reference radius; supplied source extraction radius is unspecified'
            model.report['waveform_method'] = 'Supplied r*eta(pi/2)/B0^2 * 0.004^2 / comparison_radius; no extra harmonic'
        return model

    def memory_at(self, u):
        return np.interp(u, self.mu, self.physical, left=np.nan, right=np.nan)

    def save_comparison(self, out):
        out = Path(out); out.mkdir(parents=True, exist_ok=True)
        (out/'alignment.json').write_text(json.dumps(self.report, indent=2)+'\n')
        grid = np.linspace(0, self.endpoint, 2500)
        eta = np.interp(grid, self.u, self.hp)
        memory = self.memory_at(grid)
        np.savetxt(out/'comparison.csv', np.column_stack((grid,eta,memory)), delimiter=',',
                   header='t_ret,eta_hplus_unmodified,memory_user_formula', comments='')
        fig, axes = plt.subplots(1, 2, figsize=(12,4.5), layout='constrained')
        for ax in axes:
            ax.plot(grid,eta,color='black',lw=1.7,label=r'Computed eta $h_+$')
            ax.plot(grid,memory,color=MEMORY_COLOR,lw=1.8,label='Given total memory')
            ax.set(xlabel=r'$t_{\rm ret}$',ylabel='Unamplified amplitude')
            ax.ticklabel_format(axis='y',style='sci',scilimits=(0,0))
            ax.grid(alpha=.2)
        radius_label = 'Comparison radius' if 'comparison_radius_role' in self.report else 'Extraction radius'
        axes[0].set(xlim=(0,self.endpoint),title=f"{radius_label} {self.report['coordinate_radius']:g}")
        mask=grid>=180
        values=np.r_[eta[mask],memory[mask]]
        pad=.12*float(np.ptp(values))
        axes[1].set(xlim=(180,self.endpoint),ylim=(values.min()-pad,values.max()+pad),title='Same values, enlarged tail view')
        fig.savefig(out/'memory_comparison.png',dpi=180)
        fig.savefig(out/'memory_comparison.pdf')
        plt.close(fig)


class MemoryInset:
    def __init__(self, comparison, alignment='physical'):
        if alignment != 'physical':
            raise ValueError('Only the direct user formula is supported; no empirical fitting')
        self.model=comparison
        self.fig,self.ax=plt.subplots(figsize=(7.2,3.8),dpi=120)
        self.fig.patch.set_alpha(0);self.ax.set_facecolor((0,0,0,0))
        self.wave,=self.ax.plot([],[],lw=2.6,label=r'Computed $h_+$')
        self.memory,=self.ax.plot([],[],color=MEMORY_COLOR,lw=2.6,label='Given total memory')
        self.zero,=self.ax.plot([],[],lw=1.2,alpha=.75)
        self.vertical,=self.ax.plot([],[],lw=1.2,alpha=.75)
        self.extent=1.08*float(np.max(np.abs(comparison.hp)))
        self.ax.set_ylim(-1.2*self.extent,1.2*self.extent)
        self.ax.set_xticks([]);self.ax.set_yticks([])
        self.hlabel=self.ax.text(0,0,r'$h_+$',fontsize=28,ha='right',va='center')
        self.tlabel=self.ax.text(0,0,r'$t_{\rm ret}$',fontsize=28,ha='left',va='top')
        self.scale=self.ax.text(.92,.76,'',transform=self.ax.transAxes,color='red',fontsize=32,ha='right',va='top')
        self.fig.subplots_adjust(left=.15,right=.985,bottom=.11,top=.985)

    def draw(self,current_u,gain=1.,colour='white',width=365):
        from PIL import Image
        right=self.model.endpoint;span=right
        self.ax.set_xlim(-.14*span,1.14*span)
        self.zero.set_data([0,right],[0,0]);self.vertical.set_data([0,0],[-self.extent,self.extent])
        current_u=min(current_u,right)
        visible=(self.model.u>=0)&(self.model.u<=current_u)
        # Keep the established common display gain on both comparison curves.
        wave_u=self.model.u[visible]
        wave_hp=self.model.hp[visible]
        if current_u>=0:
            wave_u=np.r_[wave_u,current_u]
            wave_hp=np.r_[wave_hp,np.interp(current_u,self.model.u,self.model.hp)]
        self.wave.set_data(wave_u,1.05*gain*wave_hp)
        mask=(self.model.mu>=0)&(self.model.mu<=current_u)
        mu=self.model.mu[mask]
        if current_u>=0:mu=np.r_[mu,current_u]
        self.memory.set_data(mu,1.05*gain*self.model.memory_at(mu))
        for artist in [self.wave,self.zero,self.vertical,self.hlabel,self.tlabel,*self.ax.spines.values()]:
            artist.set_color(colour)
        self.hlabel.set_position((-.015*span,self.extent))
        self.tlabel.set_position((1.015*span,-.03*self.extent))
        self.scale.set_text('' if gain<=1.00001 else rf'$\times {gain:.0f}$')
        self.fig.canvas.draw()
        im=Image.fromarray(np.asarray(self.fig.canvas.buffer_rgba()).copy())
        return im.resize((width,round(im.height*width/im.width)),Image.Resampling.LANCZOS)

    def close(self):
        plt.close(self.fig)
