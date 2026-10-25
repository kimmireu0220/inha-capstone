import unittest
import run


class StructureDesignTests(unittest.TestCase):
    def test_every_goal_has_all_four_structures(self):
        histories = run.benchmark()
        self.assertEqual(len(histories), 12)
        self.assertEqual(sum(map(len, histories.values())), 36)
        self.assertEqual(len({turn['request'] for turns in histories.values() for turn in turns}), 18)

    def test_reference_states_match_across_structures(self):
        histories = run.benchmark()
        for scenario in run.SCENARIOS:
            references = []
            for form in run.FORMS:
                state = dict(run.core.source.base.INITIAL)
                states = []
                for turn in histories[scenario['name']+'__'+form]:
                    state.update(turn['updates'])
                    states.append(dict(state))
                references.append(states)
            for states in references[1:]:
                self.assertEqual(states, references[0])

    def test_each_manipulation_restores_two_fields(self):
        for scenario in run.SCENARIOS:
            self.assertEqual(len(scenario['resets']), 2)
            self.assertEqual(set(scenario['resets'].values()), {'original'})
            self.assertTrue(all(value != 'original' for value in scenario['initial'].values()))


if __name__ == '__main__':
    unittest.main()
