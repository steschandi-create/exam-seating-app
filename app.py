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
            "103",
            "104",
            "201",
            "202",
            "203",
            "204",
            "301",
            "302",
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
            "Class 1",
            "Class 1",
            "Class 2",
            "Class 2",
            "Class 2",
            "Class 2",
            "Class 3",
            "Class 3",
        ],
        "Gender": ["F", "M", "M", "F", "M", "F", "M", "F", "M", "F"],
    })
    sample_data.to_excel(writer, index=False, sheet_name="Students")
  return output.getvalue()


# --- 2. MAIN APP INTERFACE & METADATA ---
st.title("🎓 Automated Exam Seating Arrangement System")
st.markdown(
    "Upload student data, configure exam details, block seats if necessary,"
    " and generate your structured reports."
)

with st.sidebar:
  st.header("1. Exam Metadata")
  exam_name = st.text_input(
      "Examination Name", "Final Semester Examination 2026"
  )
  exam_date = st.text_input("Examination Date", "2026-10-15")

  st.header("2. Input Data")
  st.download_button(
      label="📥 Download Sample Excel Template",
      data=generate_sample_excel(),
      file_name="student_template.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  )

  uploaded_file = st.file_uploader(
      "Upload Student Excel File", type=["xlsx", "xls"]
  )

  st.header("3. Room & Seating Layout Configuration")
  num_rooms = st.number_input(
      "Total Rooms Available", min_value=1, value=2, step=1
  )
  benches_per_room = st.number_input(
      "Total Benches per Room (Must be even: Left/Right pairs)",
      min_value=2,
      value=10,
      step=2,
  )

  st.header("4. Seat Blocking Option")
  block_option = st.checkbox("Block specific benches/seats?")
  blocked_benches_input = ""
  if block_option:
    blocked_benches_input = st.text_input(
        "Enter Bench Numbers to block completely (e.g., 3, 7)", "3"
    )

# --- 3. ALLOCATION & LAYOUT ENGINE ---


def create_single_gender_benches(gender_df):
  gender_df = gender_df.sort_values(by="Roll_Number", kind="mergesort")
  students = gender_df.to_dict("records")
  benches = []

  while students:
    bench = []
    classes_in_bench = set()
    remaining_students = []

    for s in students:
      if len(bench) < 4 and s["Class"] not in classes_in_bench:
        bench.append(s)
        classes_in_bench.add(s["Class"])
      else:
        remaining_students.append(s)
    students = remaining_students

    while len(bench) < 4 and students:
      bench.append(students.pop(0))

    benches.append(bench)
  return benches


if uploaded_file is not None:
  try:
    df = pd.read_excel(uploaded_file)
    st.success("Student data loaded successfully!")

    # Parse blocked benches list
    blocked_indices = []
    if block_option and blocked_benches_input:
      blocked_indices = [
          int(x.strip())
          for x in blocked_benches_input.split(",")
          if x.strip().isdigit()
      ]

    # Effective benches per room accounting for blocks
    active_benches_per_room = int(benches_per_room) - len(blocked_indices)
    total_students = len(df)
    total_capacity = int(num_rooms) * max(0, active_benches_per_room) * 4

    st.info(
        f"Total Students: **{total_students}** | Available Seating Capacity:"
        f" **{total_capacity}** (Benches blocked per room:"
        f" {len(blocked_indices)})"
    )

    if total_students > total_capacity:
      st.warning(
          "⚠️ Warning: Total students exceed available capacity! Add more"
          " rooms or unblock seats."
      )

    if st.button("🚀 Generate Exam Seating Reports"):
      df["Gender_Clean"] = df["Gender"].astype(str).str.upper().str.strip()
      df["Roll_Number"] = df["Roll_Number"].astype(str)

      df_m = df[df["Gender_Clean"] == "M"]
      df_f = df[df["Gender_Clean"] == "F"]

      benches_m = create_single_gender_benches(df_m)
      benches_f = create_single_gender_benches(df_f)

      all_benches = benches_m + benches_f
      all_benches.sort(
          key=lambda b: min([str(student["Roll_Number"]) for student in b])
      )

      num_r = int(num_rooms)
      rooms_allocation = {f"Room {r+1}": [] for r in range(num_r)}
      room_keys = list(rooms_allocation.keys())

      # Distribute benches while skipping blocked bench indices for each room
      b_idx = 0
      room_bench_counter = {rk: 1 for rk in room_keys}

      while b_idx < len(all_benches):
        for r_name in room_keys:
          current_bench_num = room_bench_counter[r_name]
          while current_bench_num in blocked_indices:
            room_bench_counter[r_name] += 1
            current_bench_num = room_bench_counter[r_name]

          if b_idx < len(all_benches):
            rooms_allocation[r_name].append({
                "bench_num": current_bench_num,
                "students": all_benches[b_idx],
            })
            b_idx += 1
            room_bench_counter[r_name] += 1

      st.markdown("---")
      st.header("📊 Generated System Reports")

      # --- BUILD MATRIX SUMMARY ---
      all_classes = sorted(df["Class"].unique())
      matrix_data = []

      for r_name, room_items in rooms_allocation.items():
        r_counts = {"Room": r_name}
        room_students = [
            student
            for item in room_items
            for student in item["students"]
        ]
        occ_df = pd.DataFrame(room_students) if room_students else pd.DataFrame()
        for cls in all_classes:
          if not occ_df.empty and "Class" in occ_df.conds if "Class" in occ_df.columns else True:
            if "Class" in occ_df.columns:
              r_counts[cls] = len(occ_df[occ_df["Class"] == cls])
            else:
              r_counts[cls] = 0
          else:
            r_counts[cls] = 0
        matrix_data.append(r_counts)

      matrix_df = pd.DataFrame(matrix_data)
      matrix_df.set_index("Room", inplace=True)
      matrix_df["Total Students"] = matrix_df.sum(axis=1)
      matrix_df.loc["Total"] = matrix_df.sum()

      # --- BUILD CLASS-WISE ROLL NUMBERS REPORT ---
      class_roll_rows = []
      for r_name, room_items in rooms_allocation.items():
        class_roll_rows.append({
            "Class / Room": f"--- {r_name} ---",
            "Student Count": "",
            "Roll Numbers": "",
        })

        room_students = [
            student
            for item in room_items
            for student in item["students"]
        ]
        if room_students:
          occ_df = pd.DataFrame(room_students)
          for cls_name, group in sorted(occ_df.groupby("Class")):
            sorted_rolls = sorted(group["Roll_Number"].tolist(), key=str)
            class_roll_rows.append({
                "Class / Room": cls_name,
                "Student Count": len(group),
                "Roll Numbers": ", ".join(sorted_rolls),
            })
        class_roll_rows.append({
            "Class / Room": "",
            "Student Count": "",
            "Roll Numbers": "",
        })

      if class_roll_rows and class_roll_rows[-1]["Class / Room"] == "":
        class_roll_rows.pop()
      class_roll_df = pd.DataFrame(class_roll_rows)

      # --- BUILD MAPPED 8-CELL ROOM SEATING PLAN (Left & Right Pairs per Row) ---
      grid_rows = []
      for r_name, room_items in rooms_allocation.items():
        grid_rows.append({
            "Bench": f"--- {r_name} ---",
            "Left Seat 1": "",
            "Left Seat 2": "",
            "Left Seat 3": "",
            "Left Seat 4": "",
            "Spacer": "",
            "Right Seat 1": "",
            "Right Seat 2": "",
            "Right Seat 3": "",
            "Right Seat 4": "",
        })

        # Group room benches into pairs (1 Left bench, 1 Right bench per physical row)
        sorted_items = sorted(room_items, key=lambda x: x["bench_num"])
        i = 0
        while i < len(sorted_items):
          left_item = sorted_items[i]
          right_item = (
              sorted_items[i + 1] if i + 1 < len(sorted_items) else None
          )

          row_data = {
              "Bench": f"Bench {left_item['bench_num']}"
              + (
                  f" & {right_item['bench_num']}"
                  if right_item
                  else " (Left Only)"
              ),
              "Left Seat 1": "",
              "Left Seat 2": "",
              "Left Seat 3": "",
              "Left Seat 4": "",
              "Spacer": "",
              "Right Seat 1": "",
              "Right Seat 2": "",
              "Right Seat 3": "",
              "Right Seat 4": "",
          }

          # Assign Left Side Students (up to 4)
          l_students = left_item["students"]
          for s_idx, s in enumerate(l_students):
            if s_idx < 4:
              row_data[f"Left Seat {s_idx+1}"] = (
                  f"{s['Roll_Number']} ({s['Name']}, {s['Class']}, {s['Gender']})"
              )

          # Assign Right Side Students (up to 4)
          if right_item:
            r_students = right_item["students"]
            for s_idx, s in enumerate(r_students):
              if s_idx < 4:
                row_data[f"Right Seat {s_idx+1}"] = (
                    f"{s['Roll_Number']} ({s['Name']}, {s['Class']}, {s['Gender']})"
                )

          grid_rows.append(row_data)
          i += 2 if right_item else 1

        grid_rows.append({
            "Bench": "",
            "Left Seat 1": "",
            "Left Seat 2": "",
            "Left Seat 3": "",
            "Left Seat 4": "",
            "Spacer": "",
            "Right Seat 1": "",
            "Right Seat 2": "",
            "Right Seat 3": "",
            "Right Seat 4": "",
        })

      if grid_rows and grid_rows[-1]["Bench"] == "":
        grid_rows.pop()
      seating_grid_df = pd.DataFrame(grid_rows)

      # --- DISPLAY TABS ON WEB PAGE ---
      tab1, tab2, tab3 = st.tabs([
          "📈 1. Summary Matrix Table",
          "📋 2. Class-Wise Roll Numbers Table",
          "📥 3. Room-Wise Seating Map Layout",
      ])

      with tab1:
        st.subheader(f"Examination: {exam_name} | Date: {exam_date}")
        st.dataframe(matrix_df, use_container_width=True)

      with tab2:
        st.subheader(f"Class-Wise Roll Numbers ({exam_name} - {exam_date})")
        st.dataframe(class_roll_df, use_container_width=True)

      with tab3:
        st.subheader(
            f"Room-Wise Physical Seating Map ({exam_name} - {exam_date})"
        )
        st.markdown(
            "_Layout showing Left Bench and Right Bench per row, with a blank"
            " spacer column._"
        )
        st.dataframe(seating_grid_df, use_container_width=True)

      # --- GENERATE EXCEL PACKAGE CONTAINING METADATA & 3 EXACT TABS ---
      excel_buffer = io.BytesIO()
      with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        # Write metadata banner onto each sheet using Pandas / Openpyxl integration if desired,
        # or structure cleanly. Here we write dataframe contents cleanly per tab:

        # Tab 1: Summary Matrix
        matrix_df.to_excel(writer, sheet_name="Summary Matrix")

        # Tab 2: Class-Wise Roll Numbers
        class_roll_df.to_excel(
            writer, sheet_name="Class-Wise Roll Numbers", index=False
        )

        # Tab 3: Room-Wise Seating Map Layout
        seating_grid_df.to_excel(
            writer, sheet_name="Room-Wise Seating Map", index=False
        )

      st.markdown("---")
      st.download_button(
          label="💾 Download 3-Tab Master Excel File with Exam Header",
          data=excel_buffer.getvalue(),
          file_name="Exam_Seating_Arrangement_Master.xlsx",
          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      )

  except Exception as e:
    st.error(f"Error reading or processing file: {e}")
else:
  st.info(
      "👈 Please configure your exam metadata and upload your student file via"
      " the sidebar."
  )
