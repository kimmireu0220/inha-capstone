import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from instruction_pipeline import process_request,load_state

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.prior=dict(jacket='green',top='white_crewneck',pin='blue_circle_left',necklace='gold_round',background='garden',prop='plant')

    def test_one_call_updates_state_and_renders_only_current_conditions(self):
        extractor=Mock();extractor.ask.return_value=json.dumps(dict(top='keep',necklace='none'))
        result=process_request(self.prior,'Reset the shirt to the source image appearance. Get rid of the necklace entirely.',extractor)
        extractor.ask.assert_called_once()
        self.assertEqual(result['state'],dict(self.prior,top='original',necklace='none'))
        self.assertIn('Keep the original top unchanged.',result['prompt'])
        self.assertIn('There must be no necklace or pendant.',result['prompt'])
        self.assertNotIn('white crew-neck shirt',result['prompt'])
        self.assertEqual(self.prior['necklace'],'gold_round')
        self.assertEqual(result['model_calls'],1)

    def test_irrelevant_changes_are_blocked_but_actual_changes_remain(self):
        extractor=Mock();extractor.ask.return_value=json.dumps(dict(pin='none',jacket='navy'))
        result=process_request(self.prior,'"Remove the pin" is a caption. Change the blazer to navy.',extractor)
        self.assertEqual(result['state'],dict(self.prior,jacket='navy'))
        self.assertEqual(result['state']['pin'],'blue_circle_left')

    def test_invalid_input_does_not_call_the_model(self):
        extractor=Mock()
        with self.assertRaises(ValueError):process_request({},'Remove the pin.',extractor)
        with self.assertRaises(ValueError):process_request(self.prior,' ',extractor)
        extractor.ask.assert_not_called()

    def test_saved_output_can_be_used_for_the_next_request(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'step.json'
            extractor=Mock();extractor.ask.return_value=json.dumps(dict(jacket='navy'))
            first=process_request(self.prior,'Change the blazer to navy.',extractor)
            path.write_text(json.dumps(first))
            extractor.ask.return_value=json.dumps(dict(prop='none'))
            second=process_request(load_state(path),'Remove the plant.',extractor)
            self.assertEqual(second['state'],dict(self.prior,jacket='navy',prop='none'))

if __name__=='__main__':unittest.main()
