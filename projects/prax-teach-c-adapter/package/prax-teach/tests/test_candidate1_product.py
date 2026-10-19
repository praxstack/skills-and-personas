"""Candidate diagnostics; frozen tests and acceptance remain unchanged."""
from types import SimpleNamespace
from ptk.project import ive, video


def test_loop_revisit_keeps_each_new_edge_occurrence():
    states = {
        'old': {'program':'p','line':8,'path':[4,5,6,7,8],'output':['f1']},
        'new': {'program':'p','line':8,'path':[4,5,6,7,8,6,7,8],'output':['f1','f2']},
    }
    lesson = SimpleNamespace(state=lambda sid:{'state':states[sid]},
                             program_source=lambda pid:'\n'.join(['int main(void) {'] + [';'] * 8 + ['return 0; }']), data={})
    plan = video.draw_plan(lesson, 'old', 'new')
    assert [(s['a'],s['b']) for s in plan['steps']] == [(8,6),(6,7),(7,8)]
    assert plan['outputs_at'] > 0.5


def test_answer_unlock_uses_visible_answer_fact_not_generic_next_scene():
    lesson = SimpleNamespace(data={'storyboard':[{'question':{'answer_fact':'answer'}}]})
    before={'cue':'m1','state':{'output':[{'fact':'sum'}]}}
    answer={'cue':'m2','state':{'output':[{'fact':'line'}], 'panel':[{'fact':'answer'}]}}
    assert ive.answer_cues(lesson,[before,answer]) == [answer]
