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
    "Configure individual room layouts, block precise side-specific seats, and"
    " generate professional reports."
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

  st.header("4. Precise Seat Blocking")
  blocked_input = st.text_area(
      "Block specific seats (Format: Room, Side Bench, Seat)\nExample: Room 1,"
      " Left Bench 2, Seat 3\nRoom 1, Right Bench 1, Seat 4",
      value="",
  )

# --- PARSE PRECISE BLOCKED SEATS ---
blocked_seats_set = set()
if blocked_input.strip():
  for line in blocked_input.split("\n"):
    parts = [p.strip() for p in line.split(",")]
    if len(parts) == 3:
      try:
        r_str = parts[0].title().strip()  # e.g., "Room 1"
        side_bench_part = (
            parts[1].lower().strip()
        )  # e.g., "left bench 2" or "right bench 1"
        seat_part = parts[2].lower().strip()  # e.g., "seat 3"

        # Extract side and local bench number
        side = "left" if "left" in side_bench_part else "right"
        b_num = int(
            side_bench_part.replace("left", "")
            .replace("right", "")
            .replace("bench", "")
            .strip()
        )
        s_num = int(seat_part.replace("seat", "").strip())

        blocked_seats_set.add((r_str, side, b_num, s_num))
      except Exception as e:
        pass

# --- 3. ALLOCATION ENGINE ---
if uploaded_file is not None:
  try:
    df = pd.read_excel(uploaded_file)
    st.success("Student data loaded successfully!")

    # Calculate exact room capacities mapping out left/right structural blocks
    total_capacity = 0
    for r_name, layout in room_layouts.items():
      valid_seats_in_room = 0
      # Left Benches
      for b in range(1, layout["left"] + 1):
        for s in range(1, 5):
          if (r_name, "left", b, s) not in blocked_seats_set:
            valid_seats_in_room += 1
      # Right Benches
      for b in range(1, layout["right"] + 1):
        for s in range(1, 5):
          if (r_name, "right", b, s) not in blocked_seats_set:
            valid_seats_in_room += 1
      total_capacity += valid_seats_in_room

    total_students = len(df)
    st.info(
        f"Total Students: **{total_students}** | Total Available Seating"
        f" Capacity: **{total_capacity}**"
    )

    if total_students > total_capacity:
      st.warning(
          "⚠️ Warning: Total students exceed available unblocked seats!"
          " Increase room benches or unblock specific seats."
      )

    if st.button("🚀 Generate Seating Reports"):
      df["Gender_Clean"] = df["Gender"].astype(str).str.upper().str.strip()
      df["Roll_Number"] = df["Roll_Number"].astype(str)

      # Sort students sequentially by roll number within classes
      df = df.sort_values(
          by=["Class", "Roll_Number"], kind="mergesort"
      ).reset_index(drop=True)


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

      # Build room structural slots considering side and bench counts
      rooms_allocation = {r_name: {"left": [], "right": []} for r_name in room_layouts.keys()}
      room_keys = list(rooms_allocation.keys())

      # Create structural slots for every room layout
      room_slots = {}
      for r_name, layout in room_layouts.items():
        slots = []
        # Left side slots
        for b in range(1, layout["left"] + 1):
          for s in range(1, 5):
            if (r_name, "left", b, s) not in blocked_seats_set:
              slots.append({"side": "left", "bench": b, "seat": s})
        # Right side slots
        for b in range(1, layout["right"] + 1):
          for s in range(1, 5):
            if (r_name, "right", b, s) not in blocked_seats_set:
              slots.append({"side": "right", "bench": b, "seat": s})
        room_slots[r_name] = slots

      # Flatten all available unblocked slots sequentially across rooms
      all_room_slots = []
      # Round-robin combine slots across rooms so students distribute evenly
      max_slots = max(len(s_list) for s_list in room_slots.values()) if room_slots else 0
      for idx in range(max_slots):
        for r_name in room_keys:
          if idx < len(room_slots[r_name]):
            all_room_slots.append(
                (r_name, room_slots[r_name][idx])
            )

      # Assign students to slots sequentially
      student_flat_list = [
          student for bench in all_benches for student in bench
      ]

      room_assigned_seats = {r_name: [] for r_name in room_keys}
      for i, student in enumerate(student_flat_list):
        if i < len(all_room_slots):
          r_name, slot_info = all_room_slots[i]
          room_assigned_seats[r_name].append({
              "side": slot_info["side"],
              "bench": slot_info["bench"],
              "seat": slot_info["seat"],
              "student": student,
          })

      st.markdown("---")
      st.header("📊 Generated System Reports")

      # --- 1. BUILD SUMMARY MATRIX ---
      all_classes = sorted(df["Class"].unique())
      matrix_data = []

      for r_name in room_keys:
        r_counts = {"Room": r_name}
        assigned = room_assigned_seats[r_name]
        room_students = [item["student"] for item in assigned]
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
      for r_name in room_keys:
        class_roll_rows.append({
            "Class / Room": f"--- {r_name} ---",
            "Student Count": "",
            "Roll Numbers": "",
        })
        assigned = room_assigned_seats[r_name]
        room_students = [item["student"] for item in assigned]
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

      # --- 3. BUILD ROOM-WISE SEATING PLAN GRID MAP ---
      seating_grid_rows = []
      for r_name in room_keys:
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

        # Organize assigned seats into a lookup dictionary
        # dict structure: ('left', bench_num, seat_num) -> student string
        seat_lookup = {}
        for item in room_assigned_seats[r_name]:
          s_key = (item["side"], item["bench"], item["seat"])
          seat_lookup[s_key] = (
              f"{item['student']['Roll_Number']} ({item['student']['Class']})"
          )

        for row_idx in range(1, max_rows + 1):
          row_data = {
              "RoomMap": r_name,
              "Left Bench No": f"Bench {row_idx}"
              if row_idx <= left_b_count
              else "",
              "L_Seat 1": seat_lookup.get(("left", row_idx, 1), "[Blocked]" if (r_name, "left", row_idx, 1) in blocked_seats_set else ""),
              "L_Seat 2": seat_lookup.get(("left", row_idx, 2), "[Blocked]" if (r_name, "left", row_idx, 2) in blocked_seats_set else ""),
              "L_Seat 3": seat_lookup.get(("left", row_idx, 3), "[Blocked]" if (r_name, "left", row_idx, 3) in blocked_seats_set else ""),
              "L_Seat 4": seat_lookup.get(("left", row_idx, 4), "[Blocked]" if (r_name, "left", row_idx, 4) in blocked_seats_set else ""),
              "Spacer": "|",
              "Right Bench No": f"Bench {row_idx}"
              if row_idx <= right_b_count
              else "",
              "R_Seat 1": seat_lookup.get(("right", row_idx, 1), "[Blocked]" if (r_name, "right", row_idx, 1) in blocked_seats_set else ""),
              "R_Seat 2": seat_lookup.get(("right", row_idx, 2), "[Blocked]" if (r_name, "right", row_idx, 2) in blocked_seats_set else ""),
              "R_Seat 3": seat_lookup.get(("right", row_idx, 3), "[Blocked]" if (r_name, "right", row_idx, 3) in blocked_seats_set else ""),
              "R_Seat 4": seat_lookup.get(("right", row_idx, 4), "[Blocked]" if (r_name, "right", row_idx, 4) in blocked_seats_set else ""),
          }
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
