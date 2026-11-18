"""Run-local publication bus. Storage is a subscriber, independent of the planner."""

import logging
from copy import deepcopy

from . import planner_store


class EventBus:
    def __init__(self, session_id, run_id):
        self.session_id = session_id
        self.run_id = run_id
        self.events = []
        self.subscribers = []

    def subscribe(self, subscriber):
        self.subscribers.append(subscriber)

    def publish(self, event):
        at = planner_store.utc_now()
        event = {
            **deepcopy(event), "session_id": self.session_id, "run_id": self.run_id,
            "seq": len(self.events) + 1, "at": at,
        }
        self.events.append(event)
        for subscriber in self.subscribers:
            try:
                subscriber(event)
            except Exception:
                # A failed subscriber must not leak payloads or interrupt the main graph.
                logging.getLogger(__name__).warning("Planner event subscriber failed for run %s", self.run_id)


class LoggingAgent:
    def __call__(self, event):
        planner_store.append_event(event)
