"""Runtime adapters for first-party modules.

Per MODS-06, modules communicate only through hub files and never via
Python imports. This package holds bot-owned runtime code that *implements*
module behaviours (state machines, consolidation, commit loops). Module
folders under modules/<name>/ contain only manifest + shell scripts +
static prompt doc.
"""
