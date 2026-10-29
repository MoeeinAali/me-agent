// Dumps the personal-site data modules as one JSON document on stdout.
// Run from the repo root:
//   pnpm dlx tsx --tsconfig ../me-frontend/tsconfig.json scripts/import/dump_site.ts > /tmp/site.json
import { profile } from "../../../me-frontend/data/profile";
import { projects } from "../../../me-frontend/data/projects";
import { experiences } from "../../../me-frontend/data/experience";
import { teachingInstitutions } from "../../../me-frontend/data/academic";
import { education, honors } from "../../../me-frontend/data/education";
import { skillCategories } from "../../../me-frontend/data/skills";
import { books } from "../../../me-frontend/data/books";
import { serviceEntries } from "../../../me-frontend/data/service";
import { organizations } from "../../../me-frontend/data/organizations";

process.stdout.write(
  JSON.stringify(
    {
      profile,
      projects,
      experience: experiences,
      teaching: teachingInstitutions,
      education,
      honors,
      skills: skillCategories,
      books,
      service: serviceEntries,
      organizations,
    },
    null,
    2,
  ),
);
