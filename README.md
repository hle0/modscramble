# modscramble

This project disects jar files into their component parts, and makes a "supermod" jar file that contains the amalgamated assets of every mod.

Then, it replaces every asset in a jar file with files from the supermod. In some cases, they're slightly modified to not cause crashes or glitchy textures.

This is specifically for Minecraft mods.

## Setup

This requires Python 3.10. There have been some issues with 3.9 in the past.

It is also recommended to install `tqdm` through `pip`, although it is not strictly required.

Example:

```sh
# Append (or create) to the supermod.jar file all the assets from Mekanism.jar and MekanismGen.jar
python3.10 concat.py supermod.jar Mekanism.jar MekanismGen.jar
# Horribly mangle Quark.jar into Quark.scrambled.jar using the files from supermod.jar, with sanity 0.8 (80% of files stay the same).
python3.10 replace.py -s 0.8 Quark.jar Quark.scrambled.jar supermod.jar 
```
