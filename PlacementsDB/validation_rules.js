// Save this as validation_rules.js and run it in MongoDB shell
db.runCommand({ collMod: "students",
    validator: {
      $jsonSchema: {
        required: ["student_id", "name", "email", "phone", "cgpa"],
        properties: {
          student_id: { bsonType: "string" },
          name: { bsonType: "string" },
          email: { bsonType: "string" },
          phone: { bsonType: "string" },
          cgpa: { bsonType: "double" }
        }
      }
    }
  });
  
  db.runCommand({ collMod: "companies",
    validator: {
      $jsonSchema: {
        required: ["company_id", "name", "location", "industry", "contact_email", "average_ctc"],
        properties: {
          company_id: { bsonType: "string" },
          name: { bsonType: "string" },
          location: { bsonType: "string" },
          industry: { bsonType: "string" },
          contact_email: { bsonType: "string" },
          average_ctc: { bsonType: "int" }
        }
      }
    }
  });
  
  db.runCommand({ collMod: "projects",
    validator: {
      $jsonSchema: {
        required: ["project_id", "title", "description", "start_date", "company_id", "student_ids", "status"],
        properties: {
          project_id: { bsonType: "string" },
          title: { bsonType: "string" },
          description: { bsonType: "string" },
          start_date: { bsonType: "date" },
          company_id: { bsonType: "string" },
          student_ids: { bsonType: "array" },
          status: { bsonType: "string" }
        }
      }
    }
  });
  
  db.runCommand({ collMod: "skills",
    validator: {
      $jsonSchema: {
        required: ["skill_id", "name", "category"],
        properties: {
          skill_id: { bsonType: "string" },
          name: { bsonType: "string" },
          category: { bsonType: "string" }
        }
      }
    }
  });
  
  db.runCommand({ collMod: "courses",
    validator: {
      $jsonSchema: {
        required: ["course_id", "name", "credits", "duration_weeks"],
        properties: {
          course_id: { bsonType: "string" },
          name: { bsonType: "string" },
          credits: { bsonType: "int" },
          duration_weeks: { bsonType: "int" }
        }
      }
    }
  });
  
  db.runCommand({ collMod: "certificates",
    validator: {
      $jsonSchema: {
        required: ["certificate_id", "name", "issuing_authority", "valid_till"],
        properties: {
          certificate_id: { bsonType: "string" },
          name: { bsonType: "string" },
          issuing_authority: { bsonType: "string" },
          valid_till: { bsonType: "date" }
        }
      }
    }
  });
  
  db.runCommand({ collMod: "publications",
    validator: {
      $jsonSchema: {
        required: ["publication_id", "title", "authors", "journal", "publication_date", "doi"],
        properties: {
          publication_id: { bsonType: "string" },
          title: { bsonType: "string" },
          authors: { bsonType: "array" },
          journal: { bsonType: "string" },
          publication_date: { bsonType: "date" },
          doi: { bsonType: "string" }
        }
      }
    }
  });
  
  db.runCommand({ collMod: "interviews",
    validator: {
      $jsonSchema: {
        required: ["interview_id", "company_id", "date", "time", "location", "interviewer", "student_ids"],
        properties: {
          interview_id: { bsonType: "string" },
          company_id: { bsonType: "string" },
          date: { bsonType: "date" },
          time: { bsonType: "string" },
          location: { bsonType: "string" },
          interviewer: { bsonType: "string" },
          student_ids: { bsonType: "array" }
        }
      }
    }
  });