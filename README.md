# spyder-opensbml
openSBML plugin for Spyder 3.2.0+

Copyright (c) 2018 Kiri Choi

## Introduction
spyder-openSBML is a plugin for [Spyder IDE](https://github.com/spyder-ide/spyder) version 3 and over. 

The plugin adds a function to directly open SBML files and create an editor window with the contents of SBML file translated to [Antimony](http://antimony.sourceforge.net/) language for added readability. 
The plugin also generates default template for [Tellurium](http://tellurium.analogmachine.org/) by placing Antimony model in Tellurim.loada function, which loads Antimony model into a new [RoadRunner](http://libroadrunner.org/) instance.

## Installation
To install, obtain the source, go to the folder where source is located and run:

`pip install .`

## Dependencies
spyder-openSBML requires Spyder IDE, Tellurium, and all of its dependencies. Tellurium is not available on PyPI yet and the dependency requirement is not enforced, so manual installation for Tellurium is required.
