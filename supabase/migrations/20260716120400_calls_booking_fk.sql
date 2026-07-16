-- calls.booking_id was left as a plain uuid in 20260716120200_calls.sql because
-- bookings didn't exist yet. Wire up the real foreign key now that it does.
alter table public.calls
  add constraint calls_booking_id_fkey
  foreign key (booking_id) references public.bookings (id) on delete set null;

create index calls_booking_id_idx on public.calls (booking_id);
