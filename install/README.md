 This folder contains patches and configuration files for dependencies of the Bolt toolchain, namely:
- DPDK patches (for DPDK 22.11.8 with meson/ninja build system)
  - `clean` contains minor cleanups that do not affect correctness, only ease of verification
- DPDK patches for the `ixgbe` driver:
  - `avoid_bit_bang` avoids unnecessary usage of bit-banging during initialization
  - `no_rxen_on_fctrl_write` ensures the FCTRL bit is written to according to the spec (reported)
  - `rdrxctl_special_writes` fixes a write to RDRXCTL according to the specification (reported)
  - `unknown_eimc_bit` removes the usage of an undocumented bit in the EIMC register (reported)
  - `unknown_ralrah` fixes the usage of undocumented Receive Address Low/High registers
  - `unknown_ralrah_2` also fixes undocumented RAL/RAH usage but the patch is a quick fix;  
    I didn't want to copy/paste the enormous function. THIS MAKES IXGBE ONLY WORK WITH THE 82599!!!
  - `unknown_swfw_sync_bit` removes the usage of an undocumented bit in the SWFW_SYNC (a.k.a. GSSR) register (reported)
  - `tdh_order_of_operations` fixes the order of enabling TX and setting TDH (reported)
  - `wrong_register_dpf_pmcf` removes the usage of bits that should be in another register on the 82599
  - `hacks` contains unfortunate hacks for verification :-(
- A minimalistic config file for `klee-uclibc`

Note: DPDK 22.11.8 uses the meson/ninja build system instead of the old make-based system. 
Some patches may not apply cleanly and may need manual adjustment. The installation script 
will warn about patches that don't apply cleanly but continue with the build process.
