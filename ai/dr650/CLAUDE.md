# DR650 project

Suzuki DR650, '98-on model. Areg's bike. This directory holds everything about it.

## Electrical — `electro/`

**Before answering anything about this bike's wiring, read `electro/README.md` and
then the specific document it points to. Do not start by opening the diagram image.**

The full factory wiring diagram has been extracted into markdown in `electro/`:
colour legend, every component and switch contact table, connector pin maps (including
the connectors where the wire colour changes from one side to the other), the complete
net list, and circuit-by-circuit walkthroughs. The image
(`electro/wiring-diagram-98plus-rotated.png`) is still the source of truth, but the
markdown answers almost everything without re-tracing it.

If you do need the image, `electro/01-reading-guide.md` has the conventions
(junction dot = connection, plain crossing = no connection), landmark coordinates, and
the crop/zoom recipe. Trace by matching colour labels at endpoints, never by following
a line across the routing field.

Anything on the actual bike that diverges from the factory diagram is Areg's own
modification — ask him rather than assuming.

## Current work

Rebuild of the damaged front harness section after a theft attempt cut the six
ignition-switch wires. See `electro/07-ignition-switch-harness.md` for the function
map, build rules and colour scheme, and `electro/08-open-questions.md` for what is
still unresolved.
