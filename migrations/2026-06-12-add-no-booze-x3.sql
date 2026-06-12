-- Adds the 'no_booze_x3' workout type.
-- Run this in the Supabase SQL Editor BEFORE deploying the updated index.html,
-- otherwise inserts of the new type will be rejected by the check constraint.

alter table workouts drop constraint workouts_type_check;
alter table workouts add constraint workouts_type_check
  check (type in ('weights', 'swimming', 'running', 'class', 'no_booze_x3'));
