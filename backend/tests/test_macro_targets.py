from types import SimpleNamespace
from backend.app.services.profile import calculate_macro_targets, calculate_calorie_range
from backend.app.services.analytics import get_today_status
from backend.app.services.nutrition_limits import daily_limits


def test_targets_follow_saved_calories():
    assert calculate_macro_targets(2000) == {'carbs': 250, 'protein': 150, 'fat': 44.44}
    assert calculate_macro_targets(1600) == {'carbs': 200, 'protein': 120, 'fat': 35.56}
    assert calculate_macro_targets(None) is None
    assert calculate_macro_targets(0) is None


def test_profile_and_existing_profile_analytics_use_same_targets():
    profile = SimpleNamespace(weight=70, height=175, age=30, sex='male',
                              activity_level='moderate', goal_type='maintain', target_calories=2000)
    calculated = calculate_calorie_range(profile)
    assert calculated['macro_targets'] == calculate_macro_targets(2000)

    class Database:
        def scalars(self, query):
            return SimpleNamespace(all=lambda: [])

        def get(self, model, user_id):
            # Older saved profiles have only target_calories; no migration/resave needed.
            return SimpleNamespace(calculation={'target_calories': 2000})

    result = get_today_status(Database(), 1)
    assert result['macro_targets'] == calculated['macro_targets']
    assert result['sugar_sodium_limits'] == {'sodium': 2000, 'sugar': 100}


def test_shared_limits_scale_sugar_but_not_sodium():
    assert daily_limits(1600) == {'sodium': 2000, 'sugar': 80}
    assert daily_limits(None) == {'sodium': 2000, 'sugar': None}
