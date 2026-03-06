from odoo.tests.common import SavepointCase
from odoo import fields


class TestHospitalBasic(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Patient = cls._model_any([
            "hospital.patient",
            "om_hospital.patient",
            "om.hospital.patient",
        ])
        cls.Doctor = cls._model_any([
            "hospital.doctor",
            "om_hospital.doctor",
            "om.hospital.doctor",
        ])
        cls.Appointment = cls._model_any([
            "hospital.appointment",
            "om_hospital.appointment",
            "om.hospital.appointment",
        ])

        cls.patient = cls.Patient.create(cls._minimal_vals(cls.Patient, name_fallback="Test Patient"))
        cls.doctor = cls.Doctor.create(cls._minimal_vals(cls.Doctor, name_fallback="Test Doctor"))

    @classmethod
    def _model_any(cls, candidates):
        last_err = None
        for m in candidates:
            try:
                return cls.env[m]
            except Exception as e:
                last_err = e
        raise AssertionError(
            f"Could not find model. Tried: {candidates}. "
            f"Run: grep -R \"_name\" -n addons/om_hospital/models/*.py"
        ) from last_err

    @classmethod
    def _minimal_vals(cls, model, name_fallback="Test", preset=None):
        """
        Build minimal vals, auto-filling required fields.
        `preset` lets the caller pre-fill required many2one fields (like patient_id).
        """
        vals = dict(preset or {})

        # Common naming fields in this tutorial module
        for fname in ("name", "doctor_name", "patient_name"):
            if fname in model._fields and fname not in vals:
                vals[fname] = name_fallback

        # Fill common required primitive fields if present
        if "gender" in model._fields and model._fields["gender"].required and "gender" not in vals:
            sel = model._fields["gender"].selection
            if sel:
                vals["gender"] = sel[0][0]

        # Generic: fill any other REQUIRED fields we can safely fill
        for fname, field in model._fields.items():
            if not field.required or fname in vals:
                continue

            if field.type == "char":
                vals[fname] = name_fallback
            elif field.type == "text":
                vals[fname] = "test"
            elif field.type == "selection":
                sel = field.selection
                if sel:
                    vals[fname] = sel[0][0]
            elif field.type == "date":
                vals[fname] = fields.Date.today()
            elif field.type == "datetime":
                vals[fname] = fields.Datetime.now()
            elif field.type in ("integer", "float", "monetary"):
                vals[fname] = 1
            elif field.type == "boolean":
                vals[fname] = True
            elif field.type == "many2one":
                # required relation must be provided via preset (or handled explicitly)
                raise AssertionError(
                    f"Model {model._name} has required many2one '{fname}' "
                    f"to {field.comodel_name}. Provide it via preset=... in the test."
                )

        return vals

    def test_01_create_patient(self):
        p = self.Patient.create(self._minimal_vals(self.Patient, name_fallback="Alice"))
        self.assertTrue(p.id)

    def test_02_create_doctor(self):
        d = self.Doctor.create(self._minimal_vals(self.Doctor, name_fallback="Dr. Bob"))
        self.assertTrue(d.id)

    def test_03_create_appointment_links_patient_doctor(self):
        preset = {}
        if "patient_id" in self.Appointment._fields:
            preset["patient_id"] = self.patient.id
        if "doctor_id" in self.Appointment._fields:
            preset["doctor_id"] = self.doctor.id

        vals = self._minimal_vals(self.Appointment, name_fallback="Appt 1", preset=preset)

        appt = self.Appointment.create(vals)
        self.assertTrue(appt.id)

        if "patient_id" in appt._fields:
            self.assertEqual(appt.patient_id, self.patient)
        if "doctor_id" in appt._fields:
            self.assertEqual(appt.doctor_id, self.doctor)

    def test_04_patient_can_post_message_if_mail_thread(self):
        p = self.patient
        if hasattr(p, "message_post"):
            msg = p.message_post(body="Unit test message")
            self.assertTrue(msg.id)
        else:
            self.assertTrue(True)

    def test_05_state_workflow_if_present(self):
        p = self.Patient.create(self._minimal_vals(self.Patient, name_fallback="State Test"))

        if "state" in p._fields:
            old = p.state
            for method in ("action_confirm", "action_approve", "action_done", "action_discharge"):
                if hasattr(p, method):
                    getattr(p, method)()
                    p.invalidate_cache()
                    self.assertNotEqual(p.state, old)
                    return

        self.assertTrue(True)
