import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('eligibility_subject',ROOT/'method.py')
subject=importlib.util.module_from_spec(spec);spec.loader.exec_module(subject)

class EligibilityTests(unittest.TestCase):
    def setUp(self):
        self.prior=dict(jacket='navy',top='white_crewneck',pin='blue_circle_left',necklace='gold_round',background='library',prop='plant')

    def test_block_irrelevant_model_changes(self):
        for text,patch in [
            ('If I later ask, reset the necklace to the source image.',{'necklace':'original'}),
            ('Do not remove the plant.',{'prop':'none'}),
            ('Never restore the original shirt.',{'top':'original'}),
            ('"Remove the pin" is a caption, not an editing instruction.',{'pin':'none'}),
        ]:
            raw=json.dumps(patch);actual,trace=subject.update(self.prior,text,[raw,raw])
            self.assertEqual(actual,self.prior,text)
            self.assertTrue(trace['ignored_instructions'])

    def test_later_direct_instruction_is_applied(self):
        for text,patch,field,value in [
            ('If asked, remove the plant. Actually, remove the plant now.',{'prop':'none'},'prop','none'),
            ('Do not remove the necklace. Actually, remove the necklace.',{'necklace':'none'},'necklace','none'),
            ('"Remove the pin" is quoted text. Change the pin to a gold square pin on the viewer-right lapel.',{'pin':'gold_square_right'},'pin','gold_square_right'),
        ]:
            raw=json.dumps(patch);actual,_=subject.update(self.prior,text,[raw,raw])
            self.assertEqual(actual[field],value,text)

    def test_unrelated_direct_change_survives(self):
        text='Do not remove the plant, but change the blazer to green.'
        raw=json.dumps(dict(prop='none',jacket='green'))
        actual,_=subject.update(self.prior,text,[raw,raw])
        self.assertEqual(actual,dict(self.prior,jacket='green'))

    def test_plain_quotation_is_not_assumed_to_be_a_caption(self):
        self.assertEqual(subject.protected_fields('Apply "remove the pin".'),{})

if __name__=='__main__':unittest.main()
