import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('scope_subject',ROOT/'method.py')
subject=importlib.util.module_from_spec(spec);spec.loader.exec_module(subject)
sys.path.insert(0,str(ROOT.parents[1]/'scripts'))
from audit_clause_invariants import cases,PRIORS,NOUNS

def new_cases():
    for prior in PRIORS:
        for restore in NOUNS:
            for keep in NOUNS:
                if restore==keep:continue
                for form in [
                    'Revert the {r} to how it looked in the source photo, keeping the {k} exactly as it is now.',
                    'Reset the {r} to the source image appearance. Maintain the {k} unchanged.',
                    'Put the {r} back as in the source photo. Leave the {k} alone.',
                    'Return the {r} to the source image. Keep the {k} as before.',
                ]:
                    yield dict(prior=dict(prior),request=form.format(r=NOUNS[restore],k=NOUNS[keep]),
                        patch={restore:'keep',keep:'original'},updates={restore:'original'})

class ScopeTests(unittest.TestCase):
    def test_historical_reference_cases(self):
        for c in cases():
            actual,_=subject.update(dict(c['prior']),c['request'],[json.dumps(c['patch'])]*2)
            self.assertEqual(actual,dict(c['prior'],**c['updates']),c['request'])

    def test_new_forms_correct_errors_without_mutating_prior(self):
        for c in new_cases():
            prior=dict(c['prior']);raw=json.dumps(c['patch'])
            actual,_=subject.update(prior,c['request'],[raw,raw])
            self.assertEqual(actual,dict(c['prior'],**c['updates']),c['request'])
            self.assertEqual(prior,c['prior'])

    def test_negative_conditional_quoted_and_unknown_objects(self):
        for text in ['Do not get rid of the plant.','Never reset the shirt to the source photo.',
                     'If requested, revert the pin to the source image.',
                     '"Get rid of the necklace" is a caption.',
                     'Put the hat back as in the source photo.']:
            normalized,evidence=subject.normalize(text)
            self.assertEqual(normalized,text)
            self.assertEqual(evidence,[])

    def test_idempotent_normalization(self):
        for c in new_cases():
            first,_=subject.normalize(c['request'])
            self.assertEqual(subject.normalize(first)[0],first)

if __name__=='__main__':unittest.main()
