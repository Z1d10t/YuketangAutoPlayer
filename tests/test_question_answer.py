import unittest

from question_answer import (
    QuestionAnswerError,
    _answer_indices,
    _extract_opencode_text,
    parse_ai_answer,
)


class QuestionAnswerTests(unittest.TestCase):
    def test_multiple_choice_mapping(self):
        answer = parse_ai_answer(
            '{"type":"multiple","answers":["A","C"],"confidence":0.95}'
        )
        self.assertEqual([0, 2], _answer_indices(answer, 4))

    def test_false_is_second_option(self):
        answer = parse_ai_answer(
            '{"type":"truefalse","answers":["错"],"confidence":0.99}'
        )
        self.assertEqual([1], _answer_indices(answer, 2))

    def test_invalid_json_is_rejected(self):
        with self.assertRaises(QuestionAnswerError):
            parse_ai_answer("答案是 A")

    def test_confidence_is_clamped(self):
        answer = parse_ai_answer(
            '{"type":"choice","answers":["B"],"confidence":1.5}'
        )
        self.assertEqual(1.0, answer.confidence)

    def test_opencode_json_event_output(self):
        output = (
            '{"type":"step_start","part":{}}\n'
            '{"type":"text","part":{"text":"{\\"type\\":\\"choice\\",'
            '\\"answers\\":[\\"B\\"],\\"confidence\\":0.9}"}}\n'
        )
        self.assertIn('"answers":["B"]', _extract_opencode_text(output))

    def test_short_answer_is_accepted(self):
        answer = parse_ai_answer(
            '{"type":"shortanswer","answers":["示例论述答案"],"confidence":0.6}'
        )
        self.assertEqual("shortanswer", answer.question_type)
        self.assertEqual(["示例论述答案"], answer.answers)


if __name__ == "__main__":
    unittest.main()
