#!/usr/bin/env python
import pytest
from pytest import approx
import xarray
import numpy as np
from pathlib import Path
from datetime import datetime
import georinex as gr
#
R = Path(__file__).parent / 'data'


def test_blank(tmp_path):
    fn = R/'blank3.10o'
    obs = gr.load(fn)
    assert obs is None

    outdir = tmp_path
    gr.load(fn, outdir)

    times = gr.gettime(fn)
    assert times is None


def test_minimal(tmp_path):
    fn = R/'minimal3.10o'
    obs = gr.load(fn)
    assert isinstance(obs, xarray.Dataset), f'{type(obs)} should be xarray.Dataset'

    outdir = tmp_path
    gr.load(fn, outdir)

    outfn = (outdir / (fn.name + '.nc'))
    assert outfn.is_file()
    assert obs.equals(gr.load(outfn)), f'{outfn}  {fn}'

    times = gr.gettime(fn)
    assert np.isnan(times.interval)


def test_meas():
    """
    test specifying specific measurements (usually only a few of the thirty or so are needed)
    """
    fn = R/'demo3.10o'
    obs = gr.load(fn)
    for v in ['L1C', 'L2P', 'C1P', 'C2P', 'C1C', 'S1C', 'S1P', 'S2P']:
        assert v in obs
    assert len(obs.data_vars) == 8
# %% one measurement
    obs = gr.load(fn, meas='C1C')
    assert 'L1C' not in obs

    C1C = obs['C1C']
    assert C1C.shape == (2, 14)  # two times, 14 SVs overall for all systems in this file

    assert (C1C.sel(sv='G07') == approx([22227666.76, 25342359.37])).all()
# %% two NON-SEQUENTIAL measurements
    obs = gr.load(fn, meas=['L1C', 'S1C'])
    assert 'L2P' not in obs

    L1C = obs['L1C']
    assert L1C.shape == (2, 14)
    assert (L1C.sel(sv='G07') == approx([118767195.32608, 133174968.81808])).all()

    S1C = obs['S1C']
    assert S1C.shape == (2, 14)

    assert (S1C.sel(sv='R23') == approx([39., 79.])).all()

    assert not C1C.equals(L1C)
# %% measurement not in some systems
    obs = gr.load(fn, meas=['S2P'])
    assert 'L2P' not in obs

    S2P = obs['S2P']
    assert S2P.shape == (2, 14)
    assert (S2P.sel(sv='G13') == approx([40., 80.])).all()
    # satellites that don't have a measurement are NaN
    # either because they weren't visible at that time
    # or simply do not make that kind of measurement at all
    R23 = S2P.sel(sv='R23')
    assert np.isnan(R23).all()
# %% measurement not in any system
    obs = gr.load(fn, meas='nonsense')
    assert 'nonsense' not in obs

    assert len(obs.data_vars) == 0
# %% wildcard
    obs = gr.load(fn, meas='C')
    assert 'L1C' not in obs
    assert 'C1P' in obs and 'C2P' in obs and 'C1C' in obs
    assert len(obs.data_vars) == 3


def test_zip():
    fn = R/'ABMF00GLP_R_20181330000_01D_30S_MO.zip'
    obs = gr.load(fn)

    assert (obs.sv.values == ['E04', 'E09', 'E12', 'E24', 'G02', 'G05', 'G06', 'G07', 'G09', 'G12', 'G13',
                              'G17', 'G19', 'G25', 'G30', 'R01', 'R02', 'R08', 'R22', 'R23', 'R24', 'S20',
                              'S31', 'S35', 'S38']).all()

    times = gr.gettime(fn).values.astype('datetime64[us]').astype(datetime)

    assert (times == [datetime(2018, 5, 13, 1, 30), datetime(2018, 5, 13, 1, 30, 30),  datetime(2018, 5, 13, 1, 31)]).all()

    hdr = gr.rinexheader(fn)
    assert hdr['t0'] <= times[0]


def test_tlim():
    fn = R/'CEDA00USA_R_20182100000_23H_15S_MO.rnx.gz'
    obs = gr.load(fn, tlim=('2018-07-29T01:17', '2018-07-29T01:18'))

    times = obs.time.values.astype('datetime64[us]').astype(datetime)

    assert (times == [datetime(2018, 7, 29, 1, 17), datetime(2018, 7, 29, 1, 17, 15),
                      datetime(2018, 7, 29, 1, 17, 45), datetime(2018, 7, 29, 1, 18)]).all()


def test_bad_system():
    with pytest.raises(KeyError):
        gr.load(R/'demo3.10o', use='Z')

    with pytest.raises(KeyError):
        gr.load(R/'demo3.10o', use=['Z', 'Y'])


def test_one_system():
    """
    ./ReadRinex.py -q tests/demo3.10o  -u G -o r3G.nc
    """
    pytest.importorskip('netCDF4')

    truth = xarray.open_dataset(R/'r3G.nc', group='OBS', autoclose=True)

    for u in ('G', ['G']):
        obs = gr.load(R/'demo3.10o', use=u)
        assert obs.equals(truth)

    assert obs.position == approx([4789028.4701, 176610.0133, 4195017.031])
    try:
        assert obs.position_geodetic == approx([41.38871005, 2.11199932, 166.25085213])
    except AttributeError:  # no pymap3d
        pass


def test_multi_system():
    """
    ./ReadRinex.py -q tests/demo3.10o  -u G R -o r3GR.nc
    """
    pytest.importorskip('netCDF4')

    use = ('G', 'R')

    obs = gr.load(R/'demo3.10o', use=use)
    truth = xarray.open_dataset(R/'r3GR.nc', group='OBS', autoclose=True)

    assert obs.equals(truth)


def test_all_system():
    """
    ./ReadRinex.py -q tests/demo3.10o -o r3all.nc
    """
    pytest.importorskip('netCDF4')

    obs = gr.load(R/'demo3.10o')
    truth = gr.rinexobs(R/'r3all.nc', group='OBS')

    assert obs.equals(truth)


def tests_all_indicators():
    """
    ./ReadRinex.py -q tests/demo3.10o -useindicators -o r3all_indicators.nc
    """
    pytest.importorskip('netCDF4')

    obs = gr.load(R/'demo3.10o', useindicators=True)
    truth = gr.rinexobs(R/'r3all_indicators.nc', group='OBS')

    assert obs.equals(truth)


def test_time_system_determination():
    obs = gr.load(R/"demo3.10o")
    assert obs.attrs['time_system'] == 'GPS'

    obs = gr.load(R/'default_time_system3.10o')
    assert obs.attrs['time_system'] == 'GAL'


if __name__ == '__main__':
    pytest.main(['-x', __file__])
