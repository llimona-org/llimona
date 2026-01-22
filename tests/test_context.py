from datetime import datetime, timedelta
from unittest import TestCase, mock

import pytest

from llimona.context import (
    ActionContext,
    Actor,
    Constraint,
    Context,
    Conversation,
    Origin,
    SensorValue,
)


class ConstraintCheckEqualsTests(TestCase):
    def test_equals_returns_true_when_values_match(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.EQUALS, value=42)

        assert constraint.check(42) is True

    def test_equals_returns_false_when_values_differ(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.EQUALS, value=42)

        assert constraint.check(43) is False


class ConstraintCheckNotEqualsTests(TestCase):
    def test_not_equals_returns_true_when_values_differ(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.NOT_EQUALS, value=42)

        assert constraint.check(43) is True

    def test_not_equals_returns_false_when_values_match(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.NOT_EQUALS, value=42)

        assert constraint.check(42) is False


class ConstraintCheckGreaterThanTests(TestCase):
    def test_greater_than_returns_true_when_sensor_value_is_greater(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.GREATER_THAN, value=10)

        assert constraint.check(11) is True

    def test_greater_than_returns_false_when_sensor_value_is_equal(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.GREATER_THAN, value=10)

        assert constraint.check(10) is False

    def test_greater_than_returns_false_when_sensor_value_is_less(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.GREATER_THAN, value=10)

        assert constraint.check(9) is False

    def test_greater_than_raises_when_sensor_value_is_not_numeric(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.GREATER_THAN, value=10)

        with pytest.raises(ValueError, match='GREATER_THAN operator requires numeric sensor value'):
            constraint.check('not-a-number')

    def test_greater_than_raises_when_constraint_value_is_not_numeric(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.GREATER_THAN, value='bad')

        with pytest.raises(ValueError, match='GREATER_THAN operator requires numeric constraint value'):
            constraint.check(5)


class ConstraintCheckLessThanTests(TestCase):
    def test_less_than_returns_true_when_sensor_value_is_less(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.LESS_THAN, value=10)

        assert constraint.check(9) is True

    def test_less_than_returns_false_when_sensor_value_is_equal(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.LESS_THAN, value=10)

        assert constraint.check(10) is False

    def test_less_than_returns_false_when_sensor_value_is_greater(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.LESS_THAN, value=10)

        assert constraint.check(11) is False

    def test_less_than_raises_when_sensor_value_is_not_numeric(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.LESS_THAN, value=10)

        with pytest.raises(ValueError, match='LESS_THAN operator requires numeric sensor value'):
            constraint.check('not-a-number')

    def test_less_than_raises_when_constraint_value_is_not_numeric(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.LESS_THAN, value='bad')

        with pytest.raises(ValueError, match='LESS_THAN operator requires numeric constraint value'):
            constraint.check(5)


class ConstraintCheckInTests(TestCase):
    def test_in_returns_true_when_sensor_value_is_in_list(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.IN, value=[1, 2, 3])

        assert constraint.check(2) is True

    def test_in_returns_false_when_sensor_value_is_not_in_list(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.IN, value=[1, 2, 3])

        assert constraint.check(4) is False

    def test_in_returns_true_when_sensor_value_is_a_key_in_dict(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.IN, value={'a': 1, 'b': 2})

        assert constraint.check('a') is True

    def test_in_returns_false_when_sensor_value_is_not_a_key_in_dict(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.IN, value={'a': 1})

        assert constraint.check('z') is False

    def test_in_raises_when_constraint_value_is_not_list_or_dict(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.IN, value=42)

        with pytest.raises(ValueError, match='IN operator requires list or dict constraint value'):
            constraint.check(42)


class ConstraintCheckNotInTests(TestCase):
    def test_not_in_returns_true_when_sensor_value_is_not_in_list(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.NOT_IN, value=[1, 2, 3])

        assert constraint.check(4) is True

    def test_not_in_returns_false_when_sensor_value_is_in_list(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.NOT_IN, value=[1, 2, 3])

        assert constraint.check(2) is False

    def test_not_in_returns_true_when_sensor_value_is_not_a_key_in_dict(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.NOT_IN, value={'a': 1})

        assert constraint.check('z') is True

    def test_not_in_returns_false_when_sensor_value_is_a_key_in_dict(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.NOT_IN, value={'a': 1})

        assert constraint.check('a') is False

    def test_not_in_raises_when_constraint_value_is_not_list_or_dict(self):
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.NOT_IN, value=42)

        with pytest.raises(ValueError, match='NOT_IN operator requires list or dict constraint value'):
            constraint.check(42)


class ConstraintCheckWithDatetimeTests(TestCase):
    def test_equals_works_with_datetime_values(self):
        dt = datetime(2026, 1, 1, 12, 0, 0)
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.EQUALS, value=dt)

        assert constraint.check(dt) is True
        assert constraint.check(datetime(2026, 1, 1, 12, 0, 1)) is False

    def test_equals_works_with_timedelta_values(self):
        td = timedelta(seconds=30)
        constraint = Constraint(provider='p', sensor='s', operator=Constraint.Operator.EQUALS, value=td)

        assert constraint.check(td) is True
        assert constraint.check(timedelta(seconds=31)) is False


# ---------------------------------------------------------------------------
# Context helpers
# ---------------------------------------------------------------------------


def _make_app():
    return mock.Mock()


def _make_action(provider: str = 'provider-a') -> ActionContext:
    return ActionContext(provider=provider, service='responses', service_action='create')


def _make_context(
    *,
    request: object = 'req',
    action: ActionContext | None = None,
    constraints: list[Constraint] | None = None,
    parent: Context | None = None,
    origin: Origin | None = None,
    actor: Actor | None = None,
    conversation: Conversation | None = None,
) -> Context:
    return Context(
        app=_make_app(),
        request=request,
        action=action,
        constraints=constraints,
        parent=parent,
        origin=origin,
        actor=actor,
        conversation=conversation,
    )


def _make_constraint(sensor: str = 'my-sensor', provider: str = 'provider-a') -> Constraint:
    return Constraint(provider=provider, sensor=sensor, operator=Constraint.Operator.EQUALS, value=1)


# ---------------------------------------------------------------------------
# Context property tests
# ---------------------------------------------------------------------------


class ContextPropertiesTests(TestCase):
    def test_request_property_returns_value_from_init(self):
        ctx = _make_context(request='my-request')

        assert ctx.request == 'my-request'

    def test_action_property_returns_value_from_init(self):
        action = _make_action()
        ctx = _make_context(action=action)

        assert ctx.action is action

    def test_origin_property_returns_value_from_init(self):
        origin = Origin(correlation_id='corr-1')
        ctx = _make_context(origin=origin)

        assert ctx.origin is origin

    def test_actor_property_returns_value_from_init(self):
        actor = Actor(id='actor-1')
        ctx = _make_context(actor=actor)

        assert ctx.actor is actor

    def test_conversation_property_returns_value_from_init(self):
        conversation = Conversation(id='conv-1')
        ctx = _make_context(conversation=conversation)

        assert ctx.conversation is conversation

    def test_parent_property_returns_none_when_no_parent(self):
        ctx = _make_context()

        assert ctx.parent is None

    def test_parent_property_returns_parent_via_weakref(self):
        parent = _make_context()
        child = _make_context(parent=parent)

        assert child.parent is parent

    def test_app_property_returns_app(self):
        app = _make_app()
        ctx = Context(app=app, request='r')

        assert ctx.app is app


# ---------------------------------------------------------------------------
# Sensor value tests
# ---------------------------------------------------------------------------


class ContextSensorValuesTests(TestCase):
    def test_add_and_get_sensor_values_returns_own_values(self):
        ctx = _make_context()
        sv = SensorValue(name='count', value=5)

        ctx.add_sensor_value(sv)

        assert list(ctx.get_sensor_values()) == [sv]

    def test_get_sensor_values_includes_successful_subcontext_values(self):
        ctx = _make_context()
        sub = _make_context()
        sv_parent = SensorValue(name='count', value=1)
        sv_child = SensorValue(name='count', value=2)
        ctx.add_sensor_value(sv_parent)
        sub.add_sensor_value(sv_child)
        ctx._subcontexts.append(sub)

        values = list(ctx.get_sensor_values())

        assert values == [sv_parent, sv_child]

    def test_get_sensor_values_excludes_failed_subcontext_by_default(self):
        ctx = _make_context()
        sub = _make_context()
        sub.set_exception(ValueError('boom'))
        sub.add_sensor_value(SensorValue(name='count', value=99))
        ctx._subcontexts.append(sub)

        values = list(ctx.get_sensor_values())

        assert values == []

    def test_get_sensor_values_includes_failed_subcontext_when_only_success_false(self):
        ctx = _make_context()
        sub = _make_context()
        sv = SensorValue(name='count', value=99)
        sub.set_exception(ValueError('boom'))
        sub.add_sensor_value(sv)
        ctx._subcontexts.append(sub)

        values = list(ctx.get_sensor_values(only_success=False))

        assert values == [sv]


# ---------------------------------------------------------------------------
# Subcontext tests
# ---------------------------------------------------------------------------


class ContextSubcontextTests(TestCase):
    def test_create_subcontext_returns_context_with_given_request_and_action(self):
        parent = _make_context(
            action=_make_action(),
            origin=Origin(correlation_id='corr-1'),
            actor=Actor(id='actor-1'),
            conversation=Conversation(id='conv-1'),
        )
        sub_action = _make_action(provider='provider-b')

        sub = parent.create_subcontext(sub_action, 'sub-req')

        assert sub.request == 'sub-req'
        assert sub.action is sub_action

    def test_create_subcontext_inherits_origin_actor_conversation_from_parent(self):
        origin = Origin(correlation_id='corr-1')
        actor = Actor(id='actor-1')
        conversation = Conversation(id='conv-1')
        parent = _make_context(origin=origin, actor=actor, conversation=conversation)

        sub = parent.create_subcontext(_make_action(), 'sub-req')

        assert sub.origin is origin
        assert sub.actor is actor
        assert sub.conversation is conversation

    def test_create_subcontext_overrides_origin_actor_conversation(self):
        parent = _make_context(
            origin=Origin(correlation_id='parent-corr'),
            actor=Actor(id='parent-actor'),
            conversation=Conversation(id='parent-conv'),
        )
        new_origin = Origin(correlation_id='child-corr')
        new_actor = Actor(id='child-actor')
        new_conv = Conversation(id='child-conv')

        sub = parent.create_subcontext(
            _make_action(),
            'sub-req',
            origin=new_origin,
            actor=new_actor,
            conversation=new_conv,
        )

        assert sub.origin is new_origin
        assert sub.actor is new_actor
        assert sub.conversation is new_conv

    def test_create_subcontext_parent_references_back(self):
        parent = _make_context()

        sub = parent.create_subcontext(_make_action(), 'sub-req')

        assert sub.parent is parent

    def test_create_subcontext_is_appended_to_parent_subcontexts(self):
        parent = _make_context()

        sub = parent.create_subcontext(_make_action(), 'sub-req')

        assert list(parent.get_subcontexts()) == [sub]

    def test_get_subcontexts_excludes_failed_by_default(self):
        parent = _make_context()
        sub = parent.create_subcontext(_make_action(), 'sub-req')
        sub.set_exception(ValueError('fail'))

        assert list(parent.get_subcontexts()) == []

    def test_get_subcontexts_includes_failed_when_only_success_false(self):
        parent = _make_context()
        sub = parent.create_subcontext(_make_action(), 'sub-req')
        sub.set_exception(ValueError('fail'))

        assert list(parent.get_subcontexts(only_success=False)) == [sub]


# ---------------------------------------------------------------------------
# Constraint tests
# ---------------------------------------------------------------------------


class ContextGetConstraintsTests(TestCase):
    def test_get_constraints_yields_matching_constraint(self):
        action = _make_action(provider='provider-a')
        constraint = _make_constraint(sensor='my-sensor', provider='provider-a')
        ctx = _make_context(action=action, constraints=[constraint])

        result = list(ctx.get_constraints('my-sensor'))

        assert result == [constraint]

    def test_get_constraints_excludes_wrong_sensor_name(self):
        action = _make_action(provider='provider-a')
        constraint = _make_constraint(sensor='other-sensor', provider='provider-a')
        ctx = _make_context(action=action, constraints=[constraint])

        result = list(ctx.get_constraints('my-sensor'))

        assert result == []

    def test_get_constraints_excludes_wrong_provider(self):
        action = _make_action(provider='provider-a')
        constraint = _make_constraint(sensor='my-sensor', provider='provider-b')
        ctx = _make_context(action=action, constraints=[constraint])

        result = list(ctx.get_constraints('my-sensor'))

        assert result == []

    def test_get_constraints_returns_nothing_when_no_action(self):
        constraint = _make_constraint(sensor='my-sensor', provider='provider-a')
        ctx = _make_context(action=None, constraints=[constraint])

        result = list(ctx.get_constraints('my-sensor'))

        assert result == []

    def test_get_constraints_propagates_to_parent(self):
        action = _make_action(provider='provider-a')
        parent_constraint = _make_constraint(sensor='my-sensor', provider='provider-a')
        parent = _make_context(action=action, constraints=[parent_constraint])
        child = parent.create_subcontext(action, 'child-req')

        result = list(child.get_constraints('my-sensor'))

        assert result == [parent_constraint]

    def test_get_constraints_returns_own_and_parent_constraints(self):
        action = _make_action(provider='provider-a')
        parent_c = _make_constraint(sensor='my-sensor', provider='provider-a')
        child_c = _make_constraint(sensor='my-sensor', provider='provider-a')
        parent = _make_context(action=action, constraints=[parent_c])
        child = parent.create_subcontext(action, 'child-req', constraints=[child_c])

        result = list(child.get_constraints('my-sensor'))

        assert result == [child_c, parent_c]


# ---------------------------------------------------------------------------
# Exception / failure tests
# ---------------------------------------------------------------------------


class ContextExceptionTests(TestCase):
    def test_is_failed_returns_false_initially(self):
        ctx = _make_context()

        assert ctx.is_failed() is False

    def test_set_exception_makes_is_failed_true(self):
        ctx = _make_context()

        ctx.set_exception(ValueError('boom'))

        assert ctx.is_failed() is True

    def test_get_exception_returns_none_initially(self):
        ctx = _make_context()

        assert ctx.get_exception() is None

    def test_get_exception_returns_set_exception(self):
        ctx = _make_context()
        exc = ValueError('boom')

        ctx.set_exception(exc)

        assert ctx.get_exception() is exc

    def test_context_manager_enter_returns_self(self):
        ctx = _make_context()

        with ctx as entered:
            assert entered is ctx

    def test_context_manager_exit_captures_exception(self):
        ctx = _make_context()
        exc = ValueError('boom')

        try:
            with ctx:
                raise exc
        except ValueError:
            pass

        assert ctx.get_exception() is exc

    def test_context_manager_exit_does_nothing_when_no_exception(self):
        ctx = _make_context()

        with ctx:
            pass

        assert ctx.is_failed() is False


# ---------------------------------------------------------------------------
# Metadata tests
# ---------------------------------------------------------------------------


class ContextMetadataTests(TestCase):
    def test_set_and_get_metadata_by_type(self):
        ctx = _make_context()
        ctx.set_metadata('key', 42)

        name, value = ctx.get_metadata(int)

        assert name == 'key'
        assert value == 42

    def test_get_metadata_by_type_and_name(self):
        ctx = _make_context()
        ctx.set_metadata('first', 1)
        ctx.set_metadata('second', 2)

        name, value = ctx.get_metadata(int, name='second')

        assert name == 'second'
        assert value == 2

    def test_get_metadata_traverses_parent(self):
        parent = _make_context()
        parent.set_metadata('key', 'parent-value')
        child = parent.create_subcontext(_make_action(), 'child-req')

        name, value = child.get_metadata(str)

        assert name == 'key'
        assert value == 'parent-value'

    def test_get_metadata_own_takes_precedence_over_parent(self):
        parent = _make_context()
        parent.set_metadata('k', 'from-parent')
        child = parent.create_subcontext(_make_action(), 'child-req')
        child.set_metadata('k', 'from-child')

        _, value = child.get_metadata(str)

        assert value == 'from-child'

    def test_get_metadata_raises_value_error_when_not_found(self):
        ctx = _make_context()

        with pytest.raises(ValueError, match='not found in context hierarchy'):
            ctx.get_metadata(int)

    def test_get_metadata_raises_value_error_with_name_when_not_found(self):
        ctx = _make_context()

        with pytest.raises(ValueError, match='"missing" not found in context hierarchy'):
            ctx.get_metadata(int, name='missing')
