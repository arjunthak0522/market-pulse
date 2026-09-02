#!/usr/bin/env python3
"""Clean Market Pulse updater entry point for the seven-signal product.

This file intentionally does not populate CPCE, NAMO or NYMO until exact source
parity is validated. It preserves the explicit unavailable state rather than
substituting a lookalike series.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONTEXT=ROOT/'data'/'market_context.json'

def main():
    data=json.loads(CONTEXT.read_text())
    data.setdefault('mcclellan',{})
    data['mcclellan'].setdefault('namo',{'status':'source_validation_required','value':None,'percentile_252d':None})
    data['mcclellan'].setdefault('nymo',{'status':'source_validation_required','value':None,'percentile_252d':None})
    data['cpce_verified']={'status':'source_validation_required','value':None,'average_5d':None,'percentile_252d':None}
    CONTEXT.write_text(json.dumps(data,indent=2)+'\n')
    print('Updated explicit source-validation states for CPCE/NAMO/NYMO')

if __name__=='__main__':main()
