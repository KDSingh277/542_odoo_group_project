from odoo.tests.common import SavepointCase
from odoo import fields


class TestFleetBasic(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Brand = cls.env["fleet.vehicle.model.brand"]
        cls.VehicleModel = cls.env["fleet.vehicle.model"]
        cls.Vehicle = cls.env["fleet.vehicle"]
        cls.Odometer = cls.env["fleet.vehicle.odometer"]
        cls.ServiceType = cls.env["fleet.service.type"]
        cls.ServiceLog = cls.env["fleet.vehicle.log.services"]
        cls.ContractLog = cls.env["fleet.vehicle.log.contract"]

        cls.brand = cls.Brand.create({"name": "Test Brand"})
        cls.model = cls.VehicleModel.create({
            "name": "Test Model",
            "brand_id": cls.brand.id,
        })
        cls.vehicle = cls.Vehicle.create({
            "model_id": cls.model.id,
            "license_plate": "TEST-001",
        })

    def _make_service_type(self, name, category):
        """Helper to satisfy required 'category' on fleet.service.type."""
        return self.ServiceType.create({
            "name": name,
            "category": category,
        })

    def test_01_vehicle_created(self):
        self.assertTrue(self.vehicle.id)
        self.assertEqual(self.vehicle.license_plate, "TEST-001")
        self.assertEqual(self.vehicle.model_id, self.model)

    def test_02_odometer_updates_vehicle(self):
        self.Odometer.create({
            "vehicle_id": self.vehicle.id,
            "value": 1234,
            "date": fields.Date.today(),
        })
        self.vehicle.invalidate_cache()
        self.assertEqual(self.vehicle.odometer, 1234)

    def test_03_latest_odometer_wins(self):
        today = fields.Date.today()
        self.Odometer.create({"vehicle_id": self.vehicle.id, "value": 100, "date": today})
        self.Odometer.create({"vehicle_id": self.vehicle.id, "value": 250, "date": today})
        self.vehicle.invalidate_cache()
        self.assertEqual(self.vehicle.odometer, 250)

    def test_04_create_service_log(self):
        st = self._make_service_type("Oil Change", "service")
        log = self.ServiceLog.create({
            "vehicle_id": self.vehicle.id,
            "service_type_id": st.id,
            "amount": 99.99,
            "date": fields.Date.today(),
            "description": "Unit test service log",
        })
        self.assertEqual(log.vehicle_id, self.vehicle)
        self.assertEqual(log.service_type_id, st)

    def test_05_create_contract_log(self):
        st = self._make_service_type("Lease", "contract")

        Contract = self.ContractLog
        today = fields.Date.today()

        vals = {
            "vehicle_id": self.vehicle.id,
            "cost_subtype_id": st.id,
            "amount": 500.0,
            "name": "Unit test contract",
        }

        # Field names differ across builds; set whichever exists
        if "date_start" in Contract._fields:
            vals["date_start"] = today
        elif "start_date" in Contract._fields:
            vals["start_date"] = today
        elif "date" in Contract._fields:
            vals["date"] = today

        if "date_end" in Contract._fields:
            vals["date_end"] = today
        elif "expiration_date" in Contract._fields:
            vals["expiration_date"] = today
        elif "end_date" in Contract._fields:
            vals["end_date"] = today

        contract = Contract.create(vals)
        self.assertEqual(contract.vehicle_id, self.vehicle)
        self.assertEqual(contract.cost_subtype_id, st)
