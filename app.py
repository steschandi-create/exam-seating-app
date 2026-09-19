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


# --- 2. MAIN APP INTERFACE ---
st.title("🎓 Advanced Exam Seating Arrangement System")
st.markdown(
    "Configure custom room layouts, block specific seats, and generate"
    " professional examination reports."
)

with st.sidebar:
  st.header("1. Exam Metadata")
  exam_name = st.text_input(
      "Examination Name", "Final Semester Examination 2026"
  )
  exam_date = st.text_input("Examination Date", "2026-10-15")

  st.header("2. Input Student Data")
  st.download_button(
      label="📥 Download Sample Excel Template",
      data=generate_sample_excel(),
      file_name="student_template.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  )
  uploaded_file = st.file_uploader(
      "Upload Student Excel File", type=["xlsx", "xls"]
  )

  st.header("3. Room & Bench Layout Configuration")
  num_rooms = st.number_input(
      "Total Rooms Available", min_value=1, value=2, step=1
  )

  room_layouts = {}
  for r in range(int(num_rooms)):
    st.subheader(f"Room {r+1} Layout")
    col1, col2 = st.columns(2)
    with col1:
      l_benches = st.number_input(
          f"Left Benches (Room {r+1})", min_value=0, value=5, step=1, key=f"l_{r}"
      )
    with col2:
      r_benches = st.number_input(
          f"Right Benches (Room {r+1})",
          min_value=0,
          value=5,
          step=1,
          key=f"r_{r}",
      )
    room_layouts[f"Room {r+1}"] = {"left": int(l_benches), "right": int(r_benches)}

  st.header("4. Seat Blocking (Optional)")
  blocked_input = st.text_area(
      "Block specific seats (Format: Room, Bench, Seat\nExample: Room 1, Bench"
      " 2, Seat 4)",
      value="",
  )

# --- PARSE BLOCKED SEATS ---
blocked_seats_set = set()
if blocked_input.strip():
  for line in blocked_input.split("\n"):
    parts = [p.strip() for p in line.split(",")]
    if len(parts) == 3:
      # e.g., Room 1, Bench 2, Seat 4 -> ("Room 1", 2, 4)
      try:
        r_str = parts[0].title()
        b_num = int(parts[1].lower().replace("bench", "").strip())
        s_num = int(parts[2].lower().replace("seat", "").strip())
        blocked_seats_set.add((r_str, b_num, s_num))
      except:
        pass

# --- 3. ALLOCATION ENGINE ---
if uploaded_file is not None:
  try:
    df = pd.read_excel(uploaded_file)
    st.success("Student data loaded successfully!")

    # Calculate total capacity considering individual room configurations
    total_capacity = 0
    room_bench_capacities = {}
    for r_name, layout in room_layouts.items():
      total_benches = layout["left"] + layout["right"]
      # Check available seats considering blocks
      valid_seats_in_room = 0
      for b in range(1, total_benches + 1):
        for s in range(1, 5):
          if (r_name, b, s) not in blocked_seats_set:
            valid_seats_in_room += 1
      room_bench_capacities[r_name] = valid_seats_in_room
      total_capacity += valid_seats_in_room

    total_students = len(df)
    st.info(
        f"Total Students: **{total_students}** | Total Available Seating"
        f" Capacity: **{total_capacity}**"
    )

    if total_students > total_capacity:
      st.warning(
          "⚠️ Warning: Total students exceed available unblocked seats!"
          " Increase room benches or unblock seats."
      )

    if st.button("🚀 Generate Seating Reports"):
      df["Gender_Clean"] = df["Gender"].astype(str).str.upper().str.strip()
      df["Roll_Number"] = df["Roll_Number"].astype(str)

      # Sort students sequentially by roll number within classes
      df = df.sort_values(
          by=["Class", "Roll_Number"], kind="mergesort"
      ).reset_index(drop=True)

      # Create single-gender bench groups (4 students per bench, distinct classes per bench)
      def create_benches(sub_df):
        students = sub_df.to_dict("records")
        benches = []
        while students:
          bench = []
          classes_in_bench = set()
          remaining = []
          for s in students:
            if len(bench) < 4 and s["Class"] not in classes_in_bench:
              bench.append(s)
              classes_in_bench.add(s["Class"])
            else:
              remaining.append(s)
          students = remaining
          while len(bench) < 4 and students:
            bench.append(students.pop(0))
          benches.append(bench)
        return benches

      benches_m = create_benches(df[df["Gender_Clean"] == "M"])
      benches_f = create_benches(df[df["Gender_Clean"] == "F"])
      all_benches = benches_m + benches_f
      all_benches.sort(
          key=lambda b: min([str(student["Roll_Number"]) for student in b])
      )

      # Distribute benches into rooms respecting room capacities & block filters
      rooms_allocation = {r_name: [] for r_name in room_layouts.keys()}
      room_keys = list(rooms_allocation.keys())

      bench_idx = 0
      for r_name in room_keys:
        layout = room_layouts[r_name]
        total_room_benches = layout["left"] + layout["right"]
        for b_num in range(1, total_room_benches + 1):
          if bench_idx < len(all_benches):
            # Form bench checking blocked seats
            bench = all_benches[bench_idx]
            # Filter out blocked seats from this bench
            filtered_bench = []
            for s_idx, student in enumerate(bench):
              seat_num = s_idx + 1
              if (r_name, b_num, seat_num) not in blocked_seats_set:
                filtered_bench.append((seat_num, student))
            rooms_allocation[r_name].append(
                {"bench_no": b_num, "occupants": filtered_bench}
            )
            bench_idx += 1

      # If any leftover benches, overflow them into rooms sequentially
      r_counter = 0
      while bench_idx < len(all_benches):
        r_name = room_keys[r_counter % len(room_keys)]
        layout = room_layouts[r_name]
        total_room_benches = layout["left"] + layout["right"]
        next_b_num = len(rooms_allocation[r_name]) + 1
        if next_b_num <= total_room_benches:
          bench = all_benches[bench_idx]
          filtered_bench = []
          for s_idx, student in enumerate(bench):
            seat_num = s_idx + 1
            if (r_name, next_b_num, seat_num) not in blocked_seats_set:
              filtered_bench.append((seat_num, student))
          rooms_allocation[r_name].append(
              {"bench_no": next_b_num, "occupants": filtered_bench}
          )
          bench_idx += 1
        r_counter += 1

      st.markdown("---")
      st.header("📊 Generated System Reports")

      # --- 1. BUILD SUMMARY MATRIX ---
      all_classes = sorted(df["Class"].unique())
      matrix_data = []

      for r_name, r_benches_list in rooms_allocation.items():
        r_counts = {"Room": r_name}
        room_students = [
            student
            for rb in r_benches_list
            for _, student in rb["occupants"]
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

      # --- 2. BUILD CLASS-WISE ROLL NUMBERS REPORT ---
      class_roll_rows = []
      for r_name, r_benches_list in rooms_allocation.items():
        class_roll_rows.append({
            "Class / Room": f"--- {r_name} ---",
            "Student Count": "",
            "Roll Numbers": "",
        })
        room_students = [
            student
            for rb in r_benches_list
            for _, student in rb["occupants"]
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
        else:
          for cls_name in all_classes:
            class_roll_rows.append({
                "Class / Room": cls_name,
                "Student Count": 0,
                "Roll Numbers": "",
            })
        class_roll_rows.append(
            {"Class / Room": "", "Student Count": "", "Roll Numbers": ""}
        )

      if class_roll_rows and class_roll_rows[-1]["Class / Room"] == "":
        class_roll_rows.pop()
      class_roll_df = pd.DataFrame(class_roll_rows)

      # --- 3. BUILD ROOM-WISE SEATING PLAN GRID (Left Bench | Spacer | Right Bench) ---
      seating_grid_rows = []
      for r_name, r_benches_list in rooms_allocation.items():
        seating_grid_rows.append({
            "Room Map": f"--- {r_name} Seating Map ---",
            "Left Bench No": "",
            "L_Seat 1": "",
            "L_Seat 2": "",
            "L_Seat 3": "",
            "L_Seat 4": "",
            "Spacer": "",
            "Right Bench No": "",
            "R_Seat 1": "",
            "R_Seat 2": "",
            "R_Seat 3": "",
            "R_Seat 4": "",
        })

        layout = room_layouts[r_name]
        left_b_count = layout["left"]
        right_b_count = layout["right"]
        max_rows = max(left_b_count, right_b_count)

        # Map benches to left and right lists
        left_benches_map = {}
        right_benches_map = {}

        for rb in r_benches_list:
          b_num = rb["bench_no"]
          # Determine if left or right based on bench index
          if b_num <= left_b_count:
            left_benches_map[b_num] = rb["occupants"]
          else:
            right_benches_map[b_num] = rb["occupants"]

        for row_idx in range(1, max_rows + 1):
          row_data = {
              "RoomMap": r_name,
              "Left Bench No": f"Bench {row_idx}"
              if row_idx <= left_b_count
              else "",
              "L_Seat 1": "",
              "L_Seat 2": "",
              "L_Seat 3": "",
              "L_Seat 4": "",
              "Spacer": "|",
              "Right Bench No": f"Bench {left_b_count + row_idx}"
              if row_idx <= right_b_count
              else "",
              "R_Seat 1": "",
              "R_Seat 2": "",
              "R_Seat 3": "",
              "R_Seat 4": "",
          }

          # Fill Left Bench
          if row_idx <= left_b_count and row_idx in left_benches_map:
            for seat_num, student in left_benches_map[row_idx]:
              row_data[f"L_Seat {seat_num}"] = (
                  f"{student['Roll_Number']} ({student['Class']})"
              )

          # Fill Right Bench (right bench numbers start after left count)
          right_b_num = left_b_count + row_idx
          if row_idx <= right_b_count and right_b_num in right_benches_map:
            for seat_num, student in right_benches_map[right_b_num]:
              row_data[f"R_Seat {seat_num}"] = (
                  f"{student['Roll_Number']} ({student['Class']})"
              )

          seating_grid_rows.append(row_data)

        seating_grid_rows.append({
            "Room Map": "",
            "Left Bench No": "",
            "L_Seat 1": "",
            "L_Seat 2": "",
            "L_Seat 3": "",
            "L_Seat 4": "",
            "Spacer": "",
            "Right Bench No": "",
            "R_Seat 1": "",
            "R_Seat 2": "",
            "R_Seat 3": "",
            "R_Seat 4": "",
        })

      if seating_grid_rows and seating_grid_rows[-1]["Room Map"] == "":
        seating_grid_rows.pop()
      seating_grid_df = pd.DataFrame(seating_grid_rows)

      # --- DISPLAY TABS ---
      tab1, tab2, tab3 = st.tabs([
          "📈 1. Summary Matrix Table",
          "📋 2. Class-Wise Roll Numbers Table",
          "📥 3. Room-Wise Seating Plans",
      ])

      with tab1:
        st.subheader(f"Exam: {exam_name} ({exam_date})")
        st.dataframe(matrix_df, use_container_width=True)

      with tab2:
        st.subheader("Class-Wise Roll Numbers per Room")
        st.dataframe(class_roll_df, use_container_width=True)

      with tab3:
        st.subheader("Physical Room Seating Grid Map")
        st.dataframe(seating_grid_df, use_container_width=True)

      # --- GENERATE EXCEL WITH METADATA HEADER ROWS ---
      excel_buffer = io.BytesIO()
      with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        # Sheet 1: Summary Matrix with Title Header
        meta_df1 = pd.DataFrame({
            "Exam Name": [exam_name],
            "Date": [exam_date],
        })
        meta_df1.to_excel(
            writer, sheet_name="Summary Matrix", index=False, startrow=0
        )
        matrix_df.to_excel(
            writer, sheet_name="Summary Matrix", startrow=3, index=True
        )

        # Sheet 2: Class-Wise Roll Numbers
        meta_df2 = pd.DataFrame({
            "Exam Name": [exam_name],
            "Date": [exam_date],
        })
        meta_df2.to_excel(
            writer,
            sheet_name="Class-Wise Roll Numbers",
            index=False,
            startrow=0,
        )
        class_roll_df.to_excel(
            writer, sheet_name="Class-Wise Roll Numbers", startrow=3, index=False
        )

        # Sheet 3: Room Seating Plans Grid
        meta_df3 = pd.DataFrame({
            "Exam Name": [exam_name],
            "Date": [exam_date],
        })
        meta_df3.to_excel(
            writer, sheet_name="Room-Wise Seating Plans", index=False, startrow=0
        )
        seating_grid_df.to_excel(
            writer, sheet_name="Room-Wise Seating Plans", startrow=3, index=False
        )

      st.markdown("---")
      st.download_button(
          label="💾 Download 3-Tab Master Excel File with Metadata",
          data=excel_buffer.getvalue(),
          file_name="Exam_Seating_Arrangement_Master.xlsx",
          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      )

  except Exception as e:
    st.error(f"Error processing data: {e}")
else:
  st.info(
      "👈 Please configure your room layouts and upload your student file using"
      " the sidebar."
  )
