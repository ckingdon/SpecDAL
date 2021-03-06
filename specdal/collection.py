# collection.py provides class for representing multiple
# spectra. Collection class is essentially a wrapper around
# pandas.DataFrame.
import pandas as pd
import numpy as np
from collections import OrderedDict
from .spectrum import Spectrum
from itertools import groupby
from .reader import read
import copy
import warnings
from os.path import abspath, expanduser, splitext
import os

################################################################################
# key functions for forming groups
def separator_keyfun(spectrum, separator, indices):
    elements = spectrum.name.split(separator)
    return separator.join([elements[i] for i in indices])
def separator_with_filler_keyfun(spectrum, separator, indices, filler='.'):
    elements = spectrum.name.split(separator)
    return separator.join([elements[i] if i in indices else
                           fill for i in range(len(elements))])

################################################################################
# main Collection class
class Collection(object):
    def __init__(self, name, directory=None, spectra=None,
                 measure_type='pct_reflect', metadata=None):
        self.name = name
        self.spectra = spectra
        self.measure_type = measure_type
        self.metadata = metadata
        if directory:
            self.read(directory, measure_type)
    @property
    def spectra(self):
        """
        A list of Spectrum objects in the collection
        """
        return list(self._spectra.values())
    @spectra.setter
    def spectra(self, value):
        self._spectra = OrderedDict()
        if value is not None:
            # assume value is an iterable such as list
            for spectrum in value:
                assert spectrum.name not in self._spectra
                self._spectra[spectrum.name] = spectrum
    @property
    def data(self):
        try:
            return pd.concat(objs=[s.measurement for s in self.spectra],
                             axis=1, keys=[s.name for s in self.spectra])
        except ValueError as err:
            # typically from duplicate index due to overlapping wavelengths
            if not all([s.stitched for s in self.spectra]):
                warnings.warn('ValueError: Try after stitching the overlaps')
            raise err
    def append(self, spectrum):
        """
        insert spectrum to the collection
        """
        assert spectrum.name not in self._spectra
        assert isinstance(spectrum, Spectrum)
        self._spectra[spectrum.name] = spectrum
    ##################################################
    # object methods
    def __getitem__(self, key):
        return self._spectra[key]
    def __delitem__(self, key):
        self._spectra.__delitem__(key)
    def __missing__(self, key):
        pass
    def __len__(self):
        return len(self._spectra)
    def __contains__(self, item):
        self._spectra.__contains__(item)
    ##################################################
    # reader
    def read(self, directory, measure_type='pct_reflect',
             ext=[".asd", ".sed", ".sig"], recursive=False,
             verbose=False):
        """
        read all files in a path matching extension
        """
        for dirpath, dirnames, filenames in os.walk(directory):
            if not recursive:
                # only read given path
                if dirpath != directory:
                    continue
            for f in sorted(filenames):
                f_name, f_ext = splitext(f)
                if f_ext not in list(ext):
                    # skip to next file
                    continue
                filepath = os.path.join(dirpath, f)
                spectrum = Spectrum(name=f_name, filepath=filepath,
                                    measure_type=measure_type,
                                    verbose=verbose)
                self.append(spectrum)
    ##################################################
    # wrapper around spectral operations
    def resample(self, spacing=1, method='slinear'):
        for spectrum in self.spectra:
            spectrum.resample(spacing, method)
    def stitch(self, method='mean'):
        for spectrum in self.spectra:
            spectrum.stitch(method)
    def jump_correct(self, splices, reference, method='additive'):
        for spectrum in self.spectra:
            spectrum.jump_correct(splices, reference, method)
    ##################################################
    # group operations
    def groupby(self, separator, indices, filler=None):
        """
        Returns
        -------
        OrderedDict consisting of specdal.Collection objects for each group
            key: group name
            value: collection object
        """
        args = [separator, indices]
        key_fun = separator_keyfun
        if filler is not None:
            args.append(filler)
            key_fun = separator_with_filler_keyfun
        spectra_sorted = sorted(self.spectra,
                                  key=lambda x: key_fun(x, *args))
        groups = groupby(spectra_sorted,
                         lambda x: key_fun(x, *args))
        result = OrderedDict()
        for g_name, g_spectra in groups:
            coll = Collection(name=g_name,
                              spectra=[copy.deepcopy(s) for s in g_spectra])
            result[coll.name] = coll
        return result
    def plot(self, *args, **kwargs):
        self.data.plot(*args, **kwargs)
        pass
    def to_csv(self, *args, **kwargs):
        self.data.transpose().to_csv(*args, **kwargs)
    ##################################################
    # aggregate
    def mean(self, append=False):
        spectrum = Spectrum(name=self.name + '_mean',
                            measurement=self.data.mean(axis=1),
                            measure_type=self.measure_type)
        if append:
            self.append(spectrum)
        return spectrum
    def median(self, append=False):
        spectrum = Spectrum(name=self.name + '_median',
                            measurement=self.data.median(axis=1),
                            measure_type=self.measure_type)
        if append:
            self.append(spectrum)
        return spectrum
    def min(self, append=False):
        spectrum = Spectrum(name=self.name + '_min',
                            measurement=self.data.min(axis=1),
                            measure_type=self.measure_type)
        if append:
            self.append(spectrum)
        return spectrum
    def max(self, append=False):
        spectrum = Spectrum(name=self.name + '_max',
                            measurement=self.data.max(axis=1),
                            measure_type=self.measure_type)
        if append:
            self.append(spectrum)
        return spectrum
    def std(self, append=False):
        spectrum = Spectrum(name=self.name + '_std',
                            measurement=self.data.std(axis=1),
                            measure_type=self.measure_type)
        if append:
            self.append(spectrum)
        return spectrum

