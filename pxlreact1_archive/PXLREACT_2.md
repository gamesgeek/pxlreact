# Plan Transition to pxlreact2
The `pxlreact` project is several years in the making and is ready for a substantial effort directed at launching: **pxlreact2**.

## Multi-Phase Plan (Don't do it all at once.)
Review the following file, and develop a plan for transitioning to `pxlreact2`; consider a *multi-phase* plan that focuses on each area of opportunity separately, allowing user and AI to iterate on that specific goal until validated. The multi-phase plan should provide a mechanism to ensure AI agents *remain aware of the overall objective* of the transition to `pxlreact2` while also knowing the *current focus* and its status.

## Reasons for pxlreact2 (Why now?)
The following factors combine to make now a good time to consider this intiative:

- *New LLM tools*: I began working on `pxlreact` several years ago when generative AI was far less capable, context windows were much smaller, and tools were less robust. I feel new tools and models like Fable offer great opportunity to improve the tool in several ways.

- *Recent Breakthroughs*: The project has recently addressed several long-standing architectural problems, including the introduction of greater thread-safety in the pixel monitoring routines, allowing for more reliable functionality that is now worth codifying

- *Tech Debt*: The age of the project means there is a lot of "technical debt" in various components, and a lot of opportunities for refactoring, consolidation, optimization, and re-engineering that could lead.

- *Inline Configuration*: The amount of manual, embedded configuration has reached a tipping point. The project is in need of a separation of concerns between the configuration and execution components; specifically, a means to define both "remaps" and "reactions" within a consolidated data file that can ideally be supplemented with an interface.

## Core Functions Remain (We're not changing what the project does, but how.)
`pxlreact2` does not seek to implement new primary functions for the project, but rather to to optimize and enhance them. They remain:

1. `Pixel Reactions` which monitor specific pixel locations for meaningful changes in color leading to a reaction in the form of a key or button press.

2. `Remap Sequences` which intercept specific inputs and translate them into outputs based on a predefined set of criteria to include pixel colors, cooldowns, and interrupt-protections.

## Improvement Opportunities
`pxlreact` has been in development by a single hobby programmer for 3+ years and has accumulated a lot of "tech debt" in that time.

A plan to transition to `pxlreact2` should addres the following opportunities:

### Opportunity #1: Lightweight GUI
This is probably the largest opportunity for `pxlreact2`. Presently, all configuration is done inline, and all feedback from the application is produced in the form of Terminal output. Developing a simple, lightweight *GUI* that allows the user to perform the most critical configuration tasks and provides key feedback in a more user-friendly and accessible format would be a massive improvement.

When planning for GUI implementation, AI should consider the following:

- `pxlreact` is a project inherently designed to "react quickly" to changes on-screen, and therefore is sensitive to performance changes. GUI libraries should be chosen and utilized to minimize impact on the core functionality (monitoring pixels and handling user key inputs)
- The features that would benefit most from GUI support are:
  - Add, edit, configure, enable/disable, delete for *pixel reactions*, as currently configured in `PxlReactionRegistry`
  - Add, edit, configure, delete for *key remap sequences*, as currently configured in `pxl_remap_maps.py`
  - Configure "wincheck" operational status by setting target window title and check-pixel parameters (consider support for multiple check pixels with dynamic add/remove options)

### Opportunity #2: External Configuration
In conjunctions with the development of a GUI, `pxlreact2` should implement one or more external configuration files to replace the current inline configuration found throughout the project, including:

- Pixel reactions (coordinates, colors, etc.) as presently defined in `PxlReactionRegistry`; care needs to be taken here since the current configuration involves associating reactions with a specific function
- Remapped key sequences and their associated readiness criteria as defined in `pxl_remap_maps.py`
- Hard-coded values for window title and "check pixel" location defined in `pxl_wincheck.py`; these values should be separated from the logic and be made configurable through the GUI ideally
- `COLOR_TOLERANCE` in `pxl_lib` and in fact the concept of a global color tolerance should be abandoned in favor of context-sensitive tolerance settings; each instance of a "color check" should pass its own tolerance threshold so that each can be adjusted for context depending on the color volatility of the space
- Keys in `pxl_keys.py`

### Opportunity #3: Performance Review & Optimization
AI should assist with a full review of the project to look for opportunities to improve performance and reliability. Some methods in the project are used occasionally, but others are invoked many times per second during operation and even a small improvement in high-frequency methods may be worthwhile.

AI should also evaluate algorithms and determine whether there are more performant or concise ways to achieve the same outcomes (i.e., using more performant structures for frequently accessed data).
Many `pxlreact` methods were written 2-3 years ago when LLMs and associated tools were far less sophisticated, so they may have made mistakes or followed inconsistent or outdated design methods.

### Opportunity #4: Rules & Documentation
The final stage of `pxlreact2` transition should be a full review of Cursor project rules and `README.md` documentation.

Rules should be updated to reflect the changes made during the transition and to retire any that appear to be out of date or to refer to functionality that is no longer present or supported.


## Considerations
When planning the phases of the transition, include the following additional considerations:

- `pyinterception` and the underlying hardware intercept driver are third party utilities and user is unfamiliar with them; do not "touch" the project at that layer, and be extremely careful with the adjacent layers such as the hardware configuration in `pxl_intercept.py` (do look for optimizations or logical improvements here)

- Do not invest any effort or design any substantial features in the interest of backward compability, `pxlreact` is a single user project and if `pxlreact2` is successful I will no longer be using it in the current state

- Beware of legacy content and do not make assumptions based on the suggestion of existing decisions related to for example GUI libraries; `pxlreact` has experimetned in the past with different approaches to a GUI so there might be some notes or comments (or rules) that talk about `tkinter` or similar.



