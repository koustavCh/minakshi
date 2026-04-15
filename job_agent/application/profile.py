from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ApplicantProfile:
    full_name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    location: str = ""
    years_experience: int = 0
    current_company: str = ""
    current_title: str = ""
    visa_sponsorship_required: Optional[bool] = None
    authorized_to_work_us: Optional[bool] = None

    def to_fill_values(self) -> Dict[str, str]:
        return {
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "linkedin": self.linkedin,
            "github": self.github,
            "location": self.location,
            "current_company": self.current_company,
            "current_title": self.current_title,
            "years_experience": str(self.years_experience) if self.years_experience else "",
        }


def load_profile_from_json(path: str) -> ApplicantProfile:
    file_path = Path(path)
    data = json.loads(file_path.read_text(encoding="utf-8"))
    return ApplicantProfile(
        full_name=str(data.get("full_name", "")),
        email=str(data.get("email", "")),
        phone=str(data.get("phone", "")),
        linkedin=str(data.get("linkedin", "")),
        github=str(data.get("github", "")),
        location=str(data.get("location", "")),
        years_experience=int(data.get("years_experience", 0) or 0),
        current_company=str(data.get("current_company", "")),
        current_title=str(data.get("current_title", "")),
        visa_sponsorship_required=(None if data.get("visa_sponsorship_required") is None else bool(data.get("visa_sponsorship_required"))),
        authorized_to_work_us=(None if data.get("authorized_to_work_us") is None else bool(data.get("authorized_to_work_us"))),
    )
