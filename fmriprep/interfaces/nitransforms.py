# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""Wrappers of NiTransforms."""

from pathlib import Path
from nipype.interfaces.base import (
    TraitedSpec, BaseInterfaceInputSpec, File,
    SimpleInterface, InputMultiObject,
    traits, isdefined,
)
from nitransforms.manip import TransformChain
from nitransforms.linear import load as load_affine

XFM_FMT = {
    ".lta": "fs",
    ".txt": "itk",
    ".mat": "itk",
    ".tfm": "itk",
}


class _ConcatenateXFMsInputSpec(BaseInterfaceInputSpec):
    in_xfms = InputMultiObject(File(exists=True), desc="input transform piles")
    inverse = traits.Bool(False, usedefault=True, desc="generate inverse")
    out_fmt = traits.Enum("itk", "fs", usedefault=True, desc="output format")
    reference = File(exists=True, desc="reference file (only for writing LTA format, if not "
                                       "concatenating another LTA).")
    moving = File(exists=True, desc="moving file (only for writing LTA format, if not "
                                    "concatenating another LTA).")


class _ConcatenateXFMsOutputSpec(TraitedSpec):
    out_xfm = File(exists=True, desc="output, combined transform")
    out_inv = File(desc="output, combined transform")


class ConcatenateXFMs(SimpleInterface):
    """Write a single, flattened transform file."""

    input_spec = _ConcatenateXFMsInputSpec
    output_spec = _ConcatenateXFMsOutputSpec

    def _run_interface(self, runtime):
        out_ext = "lta" if self.inputs.out_fmt == "fs" else "tfm"
        reference = self.inputs.reference if isdefined(self.inputs.reference) else None
        moving = self.inputs.moving if isdefined(self.inputs.moving) else None
        out_file = Path(runtime.cwd) / f"out_fwd.{out_ext}"
        self._results["out_xfm"] = str(out_file)
        out_inv = None
        if self.inputs.inverse:
            out_inv = Path(runtime.cwd) / f"out_inv.{out_ext}"
            self._results["out_inv"] = str(out_inv)

        concatenate_xfms(self.inputs.in_xfms, out_file, out_inv,
                         reference=reference, moving=moving,
                         fmt=self.inputs.out_fmt)
        return runtime


def concatenate_xfms(
    in_files,
    out_file,
    out_inv=None,
    reference=None,
    moving=None,
    fmt="itk"
):
    """Concatenate linear transforms."""
    xfm = TransformChain(
        [load_affine(f, fmt=XFM_FMT[Path(f).suffix]) for f in in_files]
    ).asaffine()
    if reference is not None and not xfm.reference:
        xfm.reference = reference

    xfm.to_filename(out_file, moving=moving, fmt=fmt)

    if out_inv is not None:
        inv_xfm = ~xfm
        if moving is not None:
            inv_xfm.reference = moving
        (~xfm).to_filename(out_inv, moving=reference, fmt=fmt)
