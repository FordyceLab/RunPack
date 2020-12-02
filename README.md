# RunPack
![ht-mek](/ht-mek_device.jpg)

## Overview
RunPack is a microfluidic valving and microscope control suite designed for HT-MEK experiments using a variety of device layouts and configurations and extensible to multiple assay types and experimental workflows. It provides hardware control of Nikon Ti microscopes via MicroManager (MMCore) and WAGO-controlled solenoid-actuated pneumatic valving. This suite sits atop the FordyceLab AcqPack to integrate logging, scripting, and image acquisition into one framework.

### Architecture
- **io**: High-level classes for software and hardware control
  - Experimental hardware access provided via the *HardwareInterface*, which allows for instantiation, control, and removal of connections to the microscope/camera/stage/sola, the WAGO, and temperature/humidity probes.
  - Experimental details including device features, general assay parameters, and logging—managed by the *ExperimentalHarness*
- **imagingcontrol**: Collection of functions for imaging at single or multiple stage positions (rastered, multi-dimensional acquisitions), for single or multiple timepoints (kinetic)
- **valvecontrol**: Collection of basic valve-control functions with error checking and logging
- **assays**: High-level classes to execute a single device assay, a linear series of assays, or multi-device scheduled assays
  - An HT-MEK-specific *Assay* class to introduce substrate and execute imaging 
  - An *AssaySeries* parent class for sequential assay execution
  - (In development) A general-purpose task-scheduling "Riffled" Assay class for simultaneous/staggered assay execution using shared hardware (camera/scope/stage)
- **mitomiprotocols**: HT-MEK-specific experimental protocols/scripts

### Setup
#### Configuration
1. config.json: A JSON configuration file specifying hardware parameters, software configuration, and experimental intial values
2. valvemap.csv: A comma-delimited file specifying valve names corresponding to specific WAGO-controlled solenoids

## Dev Notes:
- Check package requirements: use `pipreqs` on directory containing runpack 
- Install: `pip install -e git+https://github.com/FordyceLab/RunPack.git#egg=runpack`
    + Note `-e` makes package editable
- Register venv with Jupyter: `python -m ipykernel install --user --name=runpack`
- Enable GUI: `jupyter nbextension enable --py widgetsnbextension`
  + Should resolve "Widget Javascript not detected" error
