import io
import random
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Exam Seating Arrangement System", page_icon="📝", layout="wide"
)

# --- 1. DOWNLOAD SAMPLE EXCEL TEMPLATE ---


def generate_sample_excel():
  output = io.BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    sample_data = pd.DataFrame({
        "Roll_Number": [
            "101",
            "102",
            "201",
            "202",
            "301",
            "302",
            "401",
            "402",
            "501",
            "502",
        ],
        "Name": [
            "Alice",
            "Bob",
            "Charlie",
            "Diana",
            "Ethan",
            "Fiona",
            "George",
            "Hannah",
            "Ian",
            "Julia",
        ],
        "Class": [
            "Class 1",
            "Class 1",
            "Class 2",
            "Class 2",
            "Class 3",
            "Class 3",
            "Class 4",
            "Class 4",
            "Class 5",
            "Class 5",
        ],
        "Gender": ["F", "M", "M", "F", "M", "F", "M", "F", "M", "F"],
    })
    sample_data.to_excel(writer, index=False, sheet_name="Students")
  return output.getvalue()


# --- 2. MAIN APP INTERFACE ---
st.title("🎓 Automated Exam Seating Arrangement System")
st.markdown(
    "Upload your student database, configure your rooms, and download your"
    " strict 3-tab report package (Single-Gender Benches)."
)

with st.sidebar:
  st.header("1. Input Data")
  st.download_button(
      label="📥 Download Sample Excel Template",
      data=generate_sample_excel(),
      file_name="student_template.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  )

  uploaded_file = st.file_uploader(
      "Upload Student Excel File", type=["xlsx", "xls"]
  )

  st.header("2. Room Configuration")
  num_rooms = st.number_input(
      "Total Rooms Available", min_value=1, value=2, step=1
  )
  benches_per_room = st.number_input(
      "Benches per Room (Total Benches)", min_value=2, value=10, step=2
  )

# --- 3. SEATING ALLOCATION ENGINE (SINGLE-GENDER BENCHES) ---


def create_single_gender_benches(gender_df):
  students = gender_df.to_dict("records")
  random.shuffle(students)
  benches = []

  while students:
    bench = []
    classes_in_bench = set()
    remaining_students = []

    # Fill bench with up to 4 students of different classes
    for s in students:
      if len(bench) < 4 and s["Class"] not in classes_in_bench:
        bench.append(s)
        classes_in_bench.add(s["Class"])
      else:
        remaining_students.append(s)
    students = remaining_students

    # If space remains, fill with remaining students
    while len(bench) < 4 and students:
      bench.append(students.pop(0))

    benches.append(bench)
  return benches


if uploaded_file is not None:
  try:
    df = pd.read_excel(uploaded_file)
    st.success("Student data loaded successfully!")

    total_students = len(df)
    total_capacity = num_rooms * benches_per_room * 4
    st.info(
        f"Total Students: **{total_students}** | Total Room Seating Capacity:"
        f" **{total_capacity}**"
    )

    if total_students > total_capacity:
      st.warning(
          "⚠️ Warning: Total students exceed room capacity! Please add more"
          " rooms or increase benches."
      )

    if st.button("🚀 Generate Seating Reports"):
      # Separate by gender to enforce single-gender benches
      df["Gender_Clean"] = df["Gender"].astype(str).str.upper().str.strip()
      df_m = df[df["Gender_Clean"] == "M"]
      df_f = df[df["Gender_Clean"] == "F"]

      benches_m = create_single_gender_benches(df_m)
      benches_f = create_single_gender_benches(df_f)

      all_benches = benches_m + benches_f
      random.shuffle(all_benches)  # Mix male and female benches across rooms

      # Distribute benches across rooms round-robin style
      rooms_allocation = {f"Room {r+1}": [] for r in range(int(num_rooms))}
      room_keys = list(rooms_allocation.keys())

      for idx, bench in enumerate(all_benches):
        target_room = room_keys[idx % len(room_keys)]
        rooms_allocation[target_room].append(bench)

      st.markdown("---")
      st.header("📊 Generated System Reports")

      # --- BUILD MATRIX SUMMARY ---
      all_classes = sorted(df["Class"].unique())
      matrix_data = []

      for r_name, room_benches in rooms_allocation.items():
        r_counts = {"Room": r_name}
        room_students = [
            student for bench in room_benches for student in bench
        ]
        occ_df = pd.DataFrame(room_students) if room_students else pd.DataFrame()
        for cls in all_classes:
          if not occ_df.empty and "Class" in occ_df.columns:
            r_counts[cls] = len(occ_df[occ_df["Class"] == cls])
          else:
            r_counts[cls] = 0
        matrix_data.append(r_counts)

      matrix_df = pd.DataFrame(matrix_data)
      matrix_df.set_index("Room", inplace=True)
      matrix_df["Total Students"] = matrix_df.sum(axis=1)
      matrix_df.loc["Total"] = matrix_df.sum()

      # --- BUILD CLASS-WISE ROLL NUMBERS DATA ---
      class_roll_rows = []
      for r_name, room_benches in rooms_allocation.items():
        room_students = [
            student for bench in room_benches for student in bench
        ]
        if room_students:
          occ_df = pd.DataFrame(room_students)
          for cls_name, group in occ_df.groupby("Class"):
            roll_list = ", ".join(str(r) for r in group["Roll_Number"].tolist())
            class_roll_rows.append({
                "Room": r_name,
                "Class": cls_name,
                "Student Count": len(group),
                "Roll Numbers": roll_list,
            })
        else:
          for cls_name in all_classes:
            class_roll_rows.append({
                "Room": r_name,
                "Class": cls_name,
                "Student Count": 0,
                "Roll Numbers": "",
            })
      class_roll_df = pd.DataFrame(class_roll_rows)

      # --- BUILD ROOM-WISE SEATING PLANS DATA ---
      seating_plan_rows = []
      for r_name, room_benches in rooms_allocation.items():
        if room_benches:
          for b_idx, bench in enumerate(room_benches):
            for s_idx, student in enumerate(bench):
              seating_plan_rows.append({
                  "Room": r_name,
                  "Bench No": f"Bench {b_idx+1}",
                  "Side": "Left" if (s_idx < 2) else "Right",
                  "Roll Number": student["Roll_Number"],
                  "Name": student["Name"],
                  "Class": student["Class"],
                  "Gender": student["Gender"],
              })
        else:
          seating_plan_rows.append({
              "Room": r_name,
              "Bench No": "Bench 1",
              "Side": "Left",
              "Roll Number": "",
              "Name": "",
              "Class": "",
              "Gender": "",
          })
      seating_plan_df = pd.DataFrame(seating_plan_rows)

      # --- DISPLAY TABS ON WEB PAGE ---
      tab1, tab2, tab3 = st.tabs([
          "📈 1. Summary Matrix Table",
          "📋 2. Class-Wise Roll Numbers Table",
          "📥 3. Room-Wise Seating Plans",
      ])

      with tab1:
        st.subheader("Summary Matrix: Rooms vs Classes")
        st.dataframe(matrix_df, use_container_width=True)

      with tab2:
        st.subheader("Class-Wise Roll Numbers per Room")
        st.dataframe(class_roll_df, use_container_width=True)

      with tab3:
        st.subheader(
            "Complete Room-Wise Seating Plan (Strict Single-Gender Benches)"
        )
        st.dataframe(seating_plan_df, use_container_width=True)

      # --- GENERATE EXACT 3-TAB EXCEL FILE FOR DOWNLOAD ---
      excel_buffer = io.BytesIO()
      with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        matrix_df.to_excel(writer, sheet_name="Summary Matrix")
        class_roll_df.to_excel(
            writer, sheet_name="Class-Wise Roll Numbers", index=False
        )
        seating_plan_df.to_excel(
            writer, sheet_name="Room-Wise Seating Plans", index=False
        )

      st.markdown("---")
      st.download_button(
          label="💾 Download 3-Tab Master Excel File",
          data=excel_buffer.getvalue(),
          file_name="Exam_Seating_Arrangement_Master.xlsx",
          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      )

  except Exception as e:
    st.error(f"Error reading or processing the file: {e}")
else:
  st.info("👈 Please upload your student database template using the sidebar.")
