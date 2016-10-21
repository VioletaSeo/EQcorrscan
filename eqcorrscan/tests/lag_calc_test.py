"""
A series of test functions for the core functions in EQcorrscan.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest
import os
import numpy as np
import warnings

from eqcorrscan.core.lag_calc import _channel_loop, _xcorr_interp, LagCalcError
from eqcorrscan.core.lag_calc import _day_loop, _prepare_data
from eqcorrscan.core.template_gen import from_sfile
from eqcorrscan.core.match_filter import normxcorr2, DETECTION
from eqcorrscan.utils.sfile_util import read_event


class TestMethods(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.testing_path = os.path.join(os.path.abspath(
            os.path.dirname(__file__)), 'test_data', 'REA', 'TEST_')
        cls.template = from_sfile(
            sfile=os.path.join(cls.testing_path, '21-1412-02L.S201309'),
            lowcut=5, highcut=15, samp_rate=40, filt_order=4, length=3,
            swin='all', prepick=0.05)
        cls.detection = from_sfile(
            sfile=os.path.join(cls.testing_path, '21-1759-04L.S201309'),
            lowcut=5, highcut=15, samp_rate=40, filt_order=4, length=4,
            swin='all', prepick=0.55)
        cls.template_spicks = from_sfile(
            sfile=os.path.join(cls.testing_path, '18-2120-53L.S201309'),
            lowcut=5, highcut=15, samp_rate=40, filt_order=4, length=3,
            swin='all', prepick=0.05)
        cls.detection_spicks = from_sfile(
            sfile=os.path.join(cls.testing_path, '18-2350-07L.S201309'),
            lowcut=5, highcut=15, samp_rate=40, filt_order=4, length=4,
            swin='all', prepick=0.55)
        detection_event = read_event(os.path.join(cls.testing_path,
                                                  '21-1759-04L.S201309'))
        detection_spicks_event = read_event(
            os.path.join(cls.testing_path, '18-2350-07L.S201309'))
        cls.detections = [DETECTION(
            detect_time=detection_event.origins[0].time, detect_val=2.0,
            no_chans=5, threshold=1.9, typeofdet='corr', event=detection_event,
            template_name='test_template'),
                          DETECTION(
            detect_time=detection_spicks_event.origins[0].time, detect_val=2.0,
            no_chans=5, threshold=1.9, typeofdet='corr',
            event=detection_spicks_event, template_name='test_template')]
        tstart = min(tr.stats.starttime for tr in cls.template)
        cls.delays = [('test_template', [(tr.stats.station, tr.stats.channel,
                                          tr.stats.starttime - tstart)
                                         for tr in cls.template])]
        warnings.simplefilter("always")

    def test_channel_loop(self):
        """Test the main lag_calc function"""
        i, event = _channel_loop(
            detection=self.detection, template=self.template, min_cc=0.4, i=0,
            detection_id='Tester_01', interpolate=False)
        matched_traces = []
        detection_stachans = [(tr.stats.station, tr.stats.channel)
                              for tr in self.detection]
        picked_stachans = [(pick.waveform_id.station_code,
                            pick.waveform_id.channel_code)
                           for pick in event.picks]
        for master_tr in self.template:
            stachan = (master_tr.stats.station, master_tr.stats.channel)
            if stachan in detection_stachans:
                matched_traces.append(stachan)

        for picked_stachan in picked_stachans:
            self.assertTrue(picked_stachan in matched_traces)

    def channel_loop_with_spicks(self):
        with warnings.catch_warnings(record=True) as w:
            i, event = _channel_loop(
                detection=self.detection_spicks, template=self.template_spicks,
                min_cc=0.4, i=0, detection_id='Tester_01', interpolate=False)
            self.assertEqual(len(w), 0)
            self.assertTrue('Cannot check cccsum' in str(w[0]))
        matched_traces = []
        detection_stachans = [(tr.stats.station, tr.stats.channel)
                              for tr in self.detection]
        picked_stachans = [(pick.waveform_id.station_code,
                            pick.waveform_id.channel_code)
                           for pick in event.picks]
        for master_tr in self.template:
            stachan = (master_tr.stats.station, master_tr.stats.channel)
            if stachan in detection_stachans:
                matched_traces.append(stachan)

        for picked_stachan in picked_stachans:
            self.assertTrue(picked_stachan in matched_traces)

    def check_error_raised_if_cccsum_decreases(self):
        with self.assertRaises(LagCalcError):
            _channel_loop(
                detection=self.detection_spicks, template=self.template_spicks,
                min_cc=0.4, i=0, detection_id='Tester_01', interpolate=False,
                pre_lag_ccsum=2.0)

    def test_interpolate(self):
        """Test channel loop with interpolation."""
        i, event = _channel_loop(
            detection=self.detection, template=self.template, min_cc=0.4, i=0,
            detection_id='Tester_01', interpolate=True)
        matched_traces = []
        detection_stachans = [(tr.stats.station, tr.stats.channel)
                              for tr in self.detection]
        picked_stachans = [(pick.waveform_id.station_code,
                            pick.waveform_id.channel_code)
                           for pick in event.picks]
        for master_tr in self.template:
            stachan = (master_tr.stats.station, master_tr.stats.channel)
            if stachan in detection_stachans:
                matched_traces.append(stachan)

        for picked_stachan in picked_stachans:
            self.assertTrue(picked_stachan in matched_traces)

    def test_interp_normal(self):
        synth_template = np.sin(np.arange(0, 2, 0.001))
        synth_detection = synth_template[100:]
        synth_template = synth_template[0:-10]
        ccc = normxcorr2(synth_detection, synth_template)
        shift, coeff = _xcorr_interp(ccc, 0.01)
        self.assertEqual(shift.round(), 1.0)
        self.assertEqual(coeff.round(), 1.0)

    def test_interp_few_samples(self):
        synth_template = np.sin(np.arange(0, 2, 0.001))
        synth_detection = synth_template[13:]
        synth_template = synth_template[0:-10]
        ccc = normxcorr2(synth_detection, synth_template)
        shift, coeff = _xcorr_interp(ccc, 0.01)
        self.assertEqual(shift.round(), 0.0)
        self.assertEqual(coeff.round(), 1.0)

    def test_interp_not_enough_samples(self):
        synth_template = np.sin(np.arange(0, 2, 0.001))
        synth_detection = synth_template[11:]
        synth_template = synth_template[0:-10]
        ccc = normxcorr2(synth_detection, synth_template)[0]
        with self.assertRaises(IndexError):
            _xcorr_interp(ccc, 0.01)

    def test_day_loop(self):
        catalog = _day_loop(
            detection_streams=[self.detection, self.detection_spicks],
            template=self.template, min_cc=0.4, detections=self.detections,
            interpolate=False, cores=False, parallel=True)
        self.assertEqual(len(catalog), 2)
        catalog = _day_loop(
            detection_streams=[self.detection, self.detection_spicks],
            template=self.template, min_cc=0.4, detections=self.detections,
            interpolate=False, cores=False, parallel=False)
        self.assertEqual(len(catalog), 2)
        catalog = _day_loop(
            detection_streams=[self.detection, self.detection_spicks],
            template=self.template, min_cc=0.4, detections=self.detections,
            interpolate=False, cores=10, parallel=True)
        self.assertEqual(len(catalog), 2)

    def test_prepare_data(self):
        detect_streams = _prepare_data(
            detect_data=self.detection, detections=[self.detections[0]],
            zipped_templates=zip(['test_template'], [self.template]),
            delays=self.delays, shift_len=0.5, plot=False)
        self.assertEqual(len(detect_streams), 1)

    def test_no_matching_template(self):
        with warnings.catch_warnings(record=True) as w:
            detect_streams = _prepare_data(
                detect_data=self.detection, detections=[self.detections[0]],
                zipped_templates=zip(['fake_template'], [self.template]),
                delays=self.delays, shift_len=0.5, plot=False)
        self.assertTrue('No template' in str(w[0]))
        self.assertEqual(len(detect_streams), 0)

    def test_duplicate_channel_error(self):
        detect_data = self.detection + self.detection
        with self.assertRaises(LagCalcError):
            _prepare_data(
                detect_data=detect_data, detections=[self.detections[0]],
                zipped_templates=zip(['test_template'], [self.template]),
                delays=self.delays, shift_len=0.5, plot=False)


class ShortTests(unittest.TestCase):
    def test_error(self):
        with self.assertRaises(LagCalcError):
            raise LagCalcError('Generic error')
        err = LagCalcError('Generic error')
        self.assertEqual('Generic error', err.value)

    def test_bad_interp(self):
        ccc = np.array([-0.21483282, -0.59443731, 0.1898917, -0.67516038,
                        0.60129057, -0.71043723,  0.16709118, 0.96839009,
                        1.58283915, -0.3053663])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _xcorr_interp(ccc, 0.1)
        self.assertEqual(len(w), 2)
        self.assertTrue('Less than 5 samples' in str(w[0].message))
        self.assertTrue('Residual in quadratic fit' in str(w[1].message))


if __name__ == '__main__':
    unittest.main()
