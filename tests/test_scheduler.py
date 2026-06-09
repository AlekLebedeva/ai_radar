import unittest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from admin.schemas import SchedulerConfigOut
from parsers.scheduler import BackgroundScheduler


class TestBackgroundScheduler(unittest.TestCase):
    def setUp(self):
        self.session_factory = MagicMock(spec=async_sessionmaker)
        self.scheduler = BackgroundScheduler(self.session_factory)

    def tearDown(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.scheduler.stop())
            loop.close()
        except Exception:
            pass

    def test_properties(self):
        self.assertFalse(self.scheduler.running)
        self.assertEqual(len(self.scheduler._spawned), 0)

    def test_track_adds_and_removes_task(self):
        async def _test():
            async def dummy():
                pass

            t = await self.scheduler._track(dummy())
            self.assertIn(t, self.scheduler._spawned)
            await t
            await asyncio.sleep(0)
            self.assertNotIn(t, self.scheduler._spawned)

        asyncio.run(_test())

    def test_start_stop(self):
        async def _test():
            self.assertFalse(self.scheduler.running)
            await self.scheduler.start()
            self.assertTrue(self.scheduler.running)
            await self.scheduler.stop()
            self.assertFalse(self.scheduler.running)

        asyncio.run(_test())

    def test_restart_rejected(self):
        async def _test():
            await self.scheduler.start()
            self.assertTrue(self.scheduler.running)
            await self.scheduler.start()
            self.assertTrue(self.scheduler.running)
            await self.scheduler.stop()

        asyncio.run(_test())


class TestScheduleCycle(unittest.TestCase):

    def setUp(self):
        self.session_factory = MagicMock(spec=async_sessionmaker)
        self.scheduler = BackgroundScheduler(self.session_factory)

    def _make_config(self, enabled=True, interval=48):
        now = datetime.utcnow()
        return SchedulerConfigOut(
            enabled=enabled,
            interval_hours=interval,
            start_date=now,
            last_run=None,
            next_run=now,
            updated_at=now,
            created_at=now,
        )

    def create_mock_session(self):
        session = AsyncMock(spec=AsyncSession)
        return session

    def test_cycle_executes_for_active_sources(self):
        async def _test():
            db = self.create_mock_session()
            config = self._make_config()

            source_result = MagicMock()
            source_result.scalars.return_value.all.return_value = [
                MagicMock(code="huggingface", is_active=True),
                MagicMock(code="reddit", is_active=True),
            ]
            db.execute = AsyncMock(return_value=source_result)

            self.session_factory.return_value.__aenter__.return_value = AsyncMock()

            with patch("parsers.scheduler.get_parser_spec") as mock_spec:
                mock_spec.return_value = MagicMock(implemented=True)
                with patch("parsers.scheduler.TaskService") as mock_ts:
                    ts_instance = AsyncMock()
                    ts_instance.create = AsyncMock()
                    ts_instance.create.return_value = MagicMock(id="test-id")
                    mock_ts.return_value = ts_instance

                    with patch.object(self.scheduler, "_track") as mock_track:
                        mock_track.return_value = asyncio.sleep(0)

                        await self.scheduler._run_cycle(db, config)

                        self.assertEqual(ts_instance.create.call_count, 2)
                        self.assertEqual(mock_track.call_count, 2)

        asyncio.run(_test())

    def test_cycle_skips_inactive_sources(self):
        async def _test():
            db = self.create_mock_session()
            config = self._make_config()

            source_result = MagicMock()
            source_result.scalars.return_value.all.return_value = [
                MagicMock(code="reddit", is_active=True),
            ]
            db.execute = AsyncMock(return_value=source_result)

            with patch("parsers.scheduler.get_parser_spec") as mock_spec:
                mock_spec.return_value = MagicMock(implemented=True)
                with patch("parsers.scheduler.SchedulerService") as mock_svc:
                    svc = AsyncMock()
                    mock_svc.return_value = svc
                    with patch("parsers.scheduler.TaskService") as mock_ts:
                        ts_instance = AsyncMock()
                        ts_instance.create = AsyncMock()
                        ts_instance.create.return_value = MagicMock(id="test-id")
                        mock_ts.return_value = ts_instance

                        with patch.object(self.scheduler, "_track") as mock_track:
                            mock_track.return_value = asyncio.sleep(0)

                            await self.scheduler._run_cycle(db, config)

                            ts_instance.create.assert_called_once()
                            created_args = ts_instance.create.call_args[0]
                            self.assertEqual(created_args[0].parser_name, "reddit")

        asyncio.run(_test())

    def test_cycle_query_filters_active_only(self):
        async def _test():
            db = self.create_mock_session()
            config = self._make_config()

            source_result = MagicMock()
            source_result.scalars.return_value.all.return_value = [
                MagicMock(code="huggingface", is_active=True),
            ]
            db.execute = AsyncMock(return_value=source_result)

            with patch("parsers.scheduler.SchedulerService") as mock_svc:
                svc = AsyncMock()
                mock_svc.return_value = svc
                with patch("parsers.scheduler.TaskService") as mock_ts:
                    ts = AsyncMock()
                    ts.create = AsyncMock()
                    ts.create.return_value = MagicMock(id="test-id")
                    mock_ts.return_value = ts
                    with patch.object(self.scheduler, "_track") as mock_track:
                        mock_track.return_value = asyncio.sleep(0)
                        await self.scheduler._run_cycle(db, config)

            call_args = db.execute.call_args
            self.assertIsNotNone(call_args)
            call_repr = str(call_args[0][0])
            self.assertIn("sources", call_repr)
            self.assertIn("is_active", call_repr)

        asyncio.run(_test())

    def test_cycle_skips_unimplemented_specs(self):
        async def _test():
            db = self.create_mock_session()
            config = self._make_config()

            source_result = MagicMock()
            source_result.scalars.return_value.all.return_value = [
                MagicMock(code="github", is_active=True),
            ]
            db.execute = AsyncMock(return_value=source_result)

            with patch("parsers.scheduler.get_parser_spec") as mock_spec:
                mock_spec.return_value = MagicMock(implemented=False)
                with patch("parsers.scheduler.TaskService") as mock_ts:
                    ts_instance = AsyncMock()
                    ts_instance.create = AsyncMock()
                    mock_ts.return_value = ts_instance

                    with patch.object(self.scheduler, "_track") as mock_track:
                        await self.scheduler._run_cycle(db, config)

                        ts_instance.create.assert_not_called()
                        mock_track.assert_not_called()

        asyncio.run(_test())

    def test_cycle_skips_when_no_active_sources(self):
        async def _test():
            db = self.create_mock_session()
            config = self._make_config()

            source_result = MagicMock()
            source_result.scalars.return_value.all.return_value = []
            db.execute = AsyncMock(return_value=source_result)

            with patch("parsers.scheduler.SchedulerService") as mock_svc:
                svc_instance = AsyncMock()
                mock_svc.return_value = svc_instance

                await self.scheduler._run_cycle(db, config)

                svc_instance.update_last_run.assert_called_once()

        asyncio.run(_test())

    def test_check_and_run_when_disabled_skips_cycle(self):
        async def _test():
            db = self.create_mock_session()
            config = self._make_config(enabled=False)

            svc = AsyncMock()
            svc.get_config = AsyncMock(return_value=config)
            svc.update_last_run = AsyncMock()

            with patch("parsers.scheduler.SchedulerService", return_value=svc):
                with patch.object(self.scheduler, "_run_cycle") as mock_cycle:
                    await self.scheduler._check_and_run(db)
                    mock_cycle.assert_not_called()

        asyncio.run(_test())

    def test_check_and_run_when_no_config_skips_cycle(self):
        async def _test():
            db = self.create_mock_session()

            svc = AsyncMock()
            svc.get_config = AsyncMock(return_value=None)
            svc.update_last_run = AsyncMock()

            with patch("parsers.scheduler.SchedulerService", return_value=svc):
                with patch.object(self.scheduler, "_run_cycle") as mock_cycle:
                    await self.scheduler._check_and_run(db)
                    mock_cycle.assert_not_called()

        asyncio.run(_test())

    def test_check_and_run_when_future_next_run_skips_cycle(self):
        async def _test():
            db = self.create_mock_session()
            far_future = datetime.utcnow() + timedelta(hours=24)
            config = self._make_config(enabled=True)
            config.next_run = far_future

            svc = AsyncMock()
            svc.get_config = AsyncMock(return_value=config)
            svc.update_last_run = AsyncMock()

            with patch("parsers.scheduler.SchedulerService", return_value=svc):
                with patch.object(self.scheduler, "_run_cycle") as mock_cycle:
                    await self.scheduler._check_and_run(db)
                    mock_cycle.assert_not_called()

        asyncio.run(_test())

    def test_check_and_run_calls_cycle_when_ready(self):
        async def _test():
            db = self.create_mock_session()
            past = datetime.utcnow() - timedelta(hours=1)
            config = self._make_config(enabled=True)
            config.next_run = past

            svc = AsyncMock()
            svc.get_config = AsyncMock(return_value=config)
            svc.update_last_run = AsyncMock()

            with patch("parsers.scheduler.SchedulerService", return_value=svc):
                with patch.object(self.scheduler, "_run_cycle") as mock_cycle:
                    await self.scheduler._check_and_run(db)
                    mock_cycle.assert_called_once_with(db, config)

        asyncio.run(_test())

    def test_check_and_run_initializes_next_run_when_none(self):
        async def _test():
            db = self.create_mock_session()
            config = self._make_config(enabled=True)
            config.next_run = None
            config.start_date = None

            svc = AsyncMock()
            svc.get_config = AsyncMock(return_value=config)
            svc.update_last_run = AsyncMock()

            with patch("parsers.scheduler.SchedulerService", return_value=svc):
                with patch.object(self.scheduler, "_run_cycle") as mock_cycle:
                    await self.scheduler._check_and_run(db)
                    svc.update_last_run.assert_called_once()
                    mock_cycle.assert_called_once()

        asyncio.run(_test())


class TestArraySafe(unittest.TestCase):
    def test_postgres_passthrough(self):
        with patch("parsers.engine.is_postgres", return_value=True):
            from parsers.engine import _array_safe
            self.assertEqual(_array_safe(["a", "b"]), ["a", "b"])
            self.assertIsNone(_array_safe(None))

    def test_sqlite_serializes_to_json(self):
        with patch("parsers.engine.is_postgres", return_value=False):
            from parsers.engine import _array_safe
            result = _array_safe(["a", "b"])
            self.assertIsInstance(result, str)
            self.assertEqual(result, '["a", "b"]')
            self.assertIsNone(_array_safe(None))

    def test_sqlite_empty_array(self):
        with patch("parsers.engine.is_postgres", return_value=False):
            from parsers.engine import _array_safe
            result = _array_safe([])
            self.assertEqual(result, "[]")
