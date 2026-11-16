import matplotlib.pyplot as plt
import numpy as np
import scipy

class RandomVariable(scipy.stats.rv_continuous):
    def __init__(self, pdf, a, b):
        super().__init__(a=a, b=b)
        self.pdf = pdf
        self.norm = scipy.integrate.quad(self.pdf, a, b, epsrel=0.01)[0]

    def _pdf(self, x):
        return self.pdf(x) / self.norm

def generate_load(f, a, b, bin_size=1.0):
    v = RandomVariable(f, a, b)
    n = int(round(v.norm / bin_size))
    samples = v.rvs(size=n)
    return sorted(samples)

def make_plot(ax, profile, a, b):
    timestamps = generate_load(profile, a=a, b=b)
    bin_size = 1.0
    n_bins = int((b - a) / bin_size) + 1
    bin_edges = [bin_size*i for i in range(n_bins)]
    t = np.arange(a, b, 0.1)
    desired_shape = [profile(ti) for ti in t]

    ax.hist(timestamps, bins=bin_edges, alpha=0.3, color='green', label='Number of tasks received')
    ax.plot(t, desired_shape, alpha=0.7, linewidth=1.0, color='black', linestyle='--', label='Desired average rate')
    ax.set_xlabel('Time, minutes', fontsize=8)
    for xtick in ax.get_xticklabels() + ax.get_yticklabels():
        xtick.set_fontsize(8)

def make_dashboard(filename):
    def example_profile_1(t):
        return 10.0

    def example_profile_2(t):
        period = 30.0
        amp = 20.0
        return amp * 0.5 * (1.0 - np.cos(2.0*np.pi*(t/period)))

    np.random.seed(3725)
    plt.style.use('ggplot')

    fig, ax = plt.subplot_mosaic(
        [
            ['1'],
            ['2'],
        ],
        figsize=(4, 4*1.6))
    make_plot(ax['1'], profile=example_profile_1, a=0.0, b=60.0)
    make_plot(ax['2'], profile=example_profile_2, a=0.0, b=60.0)
    ax['1'].legend(fontsize=8, loc='upper center')
    ax['1'].set_ylim((0, 30))
    ax['2'].set_ylim((0, 30))
    ax['1'].set_yticks([0, 10, 20])
    ax['2'].set_yticks([0, 10, 20])
    ax['1'].set_xticks([0, 15, 30, 45, 60])
    ax['2'].set_xticks([0, 15, 30, 45, 60])
    fig.savefig(filename, bbox_inches='tight')

if __name__ == '__main__':
    make_dashboard('plots/load_generation.png')