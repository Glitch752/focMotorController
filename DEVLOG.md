# Small devlog

## Initial research
Time taken: ~2 hours

I determined the appropriate MOSFETs and circuitry required for field-oriented control.

## Initial PCB
Time taken: ~8 hours

I made the schematic and PCB layout in KiCad for the bare-minimum driver circuitry required for FOC. There were a few flaws with my initial design, like measuring current on the low MOSFET source, which I learned isn't sufficient for field-oriented control.

![](assets/schematic0.png)

## Iterating on the PCB
Time taken: ~3 hours

I iterated on the design to make the PCB much more compact and clean. I'm not yet aware of any issues with the new version of the PCB, so next up is software.

![](assets/board.png)
![](assets/schematic.png)

## Improve documentation
Time taken: ~30 minutes

I improved the [documentation of the project](https://github.com/Glitch752/focMotorController/blob/472c54bfc41076d94987bcc05ba8eb1525c3219e/README.md).