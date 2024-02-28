from tkinter import *
from tkinter import filedialog
import tkinter as tk
from PIL import Image
import os
import cv2
import pytesseract
import re

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 라디오 버튼 변경 시 파일 위치 삭제
def on_radio_button_change():
    entry_image_folder_location.delete(0, tk.END)

# '파일 찾기' 버튼 눌렀을 시 옵션에 알맞은 선택 창 표시
def open_file_dialog():
    selected_option = radio_var.get()

    if selected_option == "IMAGE":
        file_path = filedialog.askopenfilename(
            title="Select Image", filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
        if file_path:
            entry_image_folder_location.delete(0, tk.END)
            entry_image_folder_location.insert(0, file_path)

    elif selected_option == "FOLDER":
        folder_path = filedialog.askdirectory(title="Select Folder")
        if folder_path:
            entry_image_folder_location.delete(0, tk.END)
            entry_image_folder_location.insert(0, folder_path)

# 모든 체크 박스 클릭 시 값 변환
def on_check_button_change():
    global imei_checked, usim_checked, line_number_checked, ip_checked, system_title_checked, serial_number_checked
    imei_checked = var_imei.get()
    usim_checked = var_usim.get()
    line_number_checked = var_line_number.get()
    ip_checked = var_ip.get()
    system_title_checked = var_system_title.get()
    serial_number_checked = var_serial_number.get()

    return imei_checked, usim_checked, line_number_checked, ip_checked, system_title_checked, serial_number_checked

# 파일 생성 위치를 선택 할 수 있는 창 표시
def open_create_location(entry_widget):
    folder_path = filedialog.askdirectory(title="Select Folder")
    if folder_path:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, folder_path)

# 특별한 버전 체크 박스에 따라 입력 창과 버튼을 활성화 및 비활성화
def on_check_button_special():
    global special
    special_value = special.get()
    if special_value:
        entry_create_image_location.config(state=tk.NORMAL)
        btn_create_image_location.config(state=tk.NORMAL)

    else:
        entry_create_image_location.config(state=tk.DISABLED)
        btn_create_image_location.config(state=tk.DISABLED)

    return special

# 이미지를 스캔해서 원하는 값 리턴
def scan_IMAGE(image_folder_path, txt_file):
    imei_checked, usim_checked, line_number_checked, ip_checked, system_title_checked, serial_number_checked = on_check_button_change()

    # 각 변수를 None으로 초기화
    imei_number_match = usim_number_match = line_number_match = IP_address_match = system_title_match = serial_number_match = None

    # 이미지 파일 로드
    image = cv2.imread(image_folder_path)

    if image is None:
        print(f"Error processing in image {image_folder_path}.")
        return None

    # 이미지 전처리를 위해 흑백으로 변환
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 이미지에서 텍스트 추출
    text = pytesseract.image_to_string(gray, lang='kor+eng')

    if imei_checked:
        # IMEI 다음의 15자리 숫자 추출
        imei_number_pattern = re.compile(r'IMEI\D*(\d{15})', re.IGNORECASE)
        imei_number_match = imei_number_pattern.search(text)

    if usim_checked:
        # USIM Number 다음의 18자리 숫자 추출
        usim_number_pattern = re.compile(r'USIM Number\D*(\d{18})', re.IGNORECASE)
        usim_number_match = usim_number_pattern.search(text)

    if line_number_checked:
        # 회선번호 다음의 11자리 숫자 추출
        line_number_pattern = re.compile(r'회선번호\D*(\d{11})', re.IGNORECASE)
        line_number_match = line_number_pattern.search(text)

    if ip_checked:
        # "FDE"로 시작하는 IPv6 주소 추출
        IP_address_pattern = re.compile(r'IP\D*(FDE[\da-fA-F:]+)', re.IGNORECASE)
        IP_address_match = IP_address_pattern.search(text)

    if system_title_checked:
        # SystemTitle 뒤의 13자리 영어와 숫자 합쳐진 값 추출
        system_title_pattern = re.compile(r'SystemTitle\D*(\w{13})', re.IGNORECASE)
        system_title_match = system_title_pattern.search(text)

    if serial_number_checked:
        # Serial Number "G" 뒤의 11자리 영어와 숫자 합쳐진 값 추출
        serial_number_pattern = re.compile(r'Serial Number\D*(G\d{11})', re.IGNORECASE)
        serial_number_match = serial_number_pattern.search(text)

    extracted_info = {
        "imei": imei_number_match.group(1) if imei_number_match else None,
        "usim_number": usim_number_match.group(1) if usim_number_match else None,
        "line_number": line_number_match.group(1) if line_number_match else None,
        "IP": IP_address_match.group(1) if IP_address_match else None,
        "system_title": system_title_match.group(1) if system_title_match else None,
        "serial_number": serial_number_match.group(1) if serial_number_match else None
    }

    # 디버깅 용
    print(
        extracted_info["imei"], '\t', extracted_info["usim_number"], '\t', extracted_info["line_number"], '\t',
        extracted_info["IP"], '\t', extracted_info["system_title"], '\t', extracted_info["serial_number"])

    # Text 파일 작성 용
    txt_file.write(
        f"{extracted_info['imei']}\t{extracted_info['usim_number']}\t{extracted_info['line_number']}\t"
        f"{extracted_info['IP']}\t{extracted_info['system_title']}\t{extracted_info['serial_number']}\n")

    return extracted_info

# 폴더를 갖고와 정렬하고 위 함수를 이용해서 이미지 하나하나 스캔해서 원하는 값 리턴
def scan_FOLDER(image_folder_path, txt_file):
    create_image_path = entry_create_image_location.get()

    # 폴더 내의 모든 파일 리스트 가져오기
    file_list = os.listdir(image_folder_path)

    # 이미지 파일만 필터링하고 숫자 부분을 추출하여 정렬
    image_files = sorted([f for f in file_list if f.lower().endswith(('.png', '.jpg', '.jpeg'))], key=lambda x: int(re.search(r'\d+', x).group()))

    for image_file in image_files:
        # 이미지 파일의 전체 경로
        image_path = os.path.join(image_folder_path, image_file)

        # 이미지에서 숫자 추출
        try:
            scan_IMAGE(image_path, txt_file)
            if special.get():
                capture_and_save(image_path, create_image_path)
        except Exception as e:
            print(f"Error processing image in folder {image_path}: {e}")

# 특별한 버전에서 이미지의 특정 부분을 캡처해야 한다면, 특정 부분 캡처
def capture_and_save(image_path, create_location_image):
    # 이미지 불러오기
    image = Image.open(image_path)

    # 특정 좌표값을 사용하여 이미지를 자르기
    cropped_image = image.crop((209, 163, 1379, 801))

    # 색상 모드 변경 (RGBA → RGB)
    rgb_image = cropped_image.convert('RGB')

    # 이미지 저장 폴더에 저장
    image_number = 1
    while os.path.exists(os.path.join(create_location_image, f"{image_number}.png")):
        image_number += 1

    image_path = os.path.join(create_location_image, f"{image_number}.png")
    rgb_image.save(image_path, 'PNG')

# 리턴 받은 값을 원하는 Text 파일에 작성
def create_text_file():
    global txt_file, image_number

    selected_option = radio_var.get()   # 라디오 버튼으로 옵션 선택
    image_folder_path = entry_image_folder_location.get()   # 이미지나 폴더 선택
    create_text_path = entry_create_text_location.get()  # text 파일 저장 위치
    create_file_name = entry_create_text_name.get()  # text 파일 이름
    create_image_path = entry_create_image_location.get()   # special 버전, 이미지 잘라서 저장 위치
    special_check = special.get()

    if not image_folder_path:
        label_result.config(text="File 위치를 선택 및 입력 해주세요.")
        return

    if not create_text_path:
        label_result.config(text="Text 파일을 저장할 위치를 선택 및 입력 해주세요.")
        return

    if not create_file_name:
        label_result.config(text="Text 파일 명을 입력 해주세요.")
        return

    if special_check:
        if not create_image_path:
            label_result.config(text="Image를 저장할 위치를 선택 및 입력 해주세요")
            return

    try:
        with open(f"{create_text_path}/{create_file_name}.txt", 'w') as txt_file:
            if selected_option == "IMAGE":
                scan_IMAGE(image_folder_path, txt_file)
                if special.get():
                    capture_and_save(image_folder_path, create_image_path)

            elif selected_option == "FOLDER":
                scan_FOLDER(image_folder_path, txt_file)

        if special_check:
            label_result.config(
                text=f"Text 파일 명: '{create_file_name}.txt' / 경로: Text= '{create_text_path}' / Image= '{create_image_path}'")

        else:
            label_result.config(
                text=f"Text 파일 명: '{create_file_name}.txt' / 경로: Text= '{create_text_path}'")

    except Exception as e:
        label_result.config(text=f"Error: {e}")
        print(f"Error creating file: {e}")


# Tkinter 창 생성
window = tk.Tk()
window.title("Search for characters and Image capture and save")
window.geometry("750x400")
window.resizable(False, False)

# 라디오 버튼을 위한 변수 선언
radio_var = tk.StringVar()

# 체크 버튼을 위한 변수 선언
var_imei = tk.StringVar()
var_usim = tk.StringVar()
var_line_number = tk.StringVar()
var_ip = tk.StringVar()
var_system_title = tk.StringVar()
var_serial_number = tk.StringVar()

label_file_option = tk.Label(window, text="File 옵션:")
label_file_option.grid(row=0, column=0, pady=10, padx=20, sticky="w")

# 라디오 버튼 생성
radio_button1 = tk.Radiobutton(window, text="IMAGE", variable=radio_var, value="IMAGE", command=on_radio_button_change)
radio_button2 = tk.Radiobutton(window, text="FOLDER", variable=radio_var, value="FOLDER", command=on_radio_button_change)

# 라디오 버튼 좌우로 배치
radio_button1.grid(row=0, column=1, pady=10, padx=20, sticky="w")
radio_button2.grid(row=0, column=2, pady=10, padx=20, sticky="w")

# 올려야되는 파일 형식
label_file_setting = tk.Label(window, text="파일은 한글이 아닌 숫자나 영어")
label_file_setting.grid(row=0, column=3, pady=10, padx=0, sticky="w")

# 파일 위치를 보여줄 라벨 생성
label_image_folder_location = tk.Label(window, text="File 위치:")
label_image_folder_location.grid(row=1, column=0, pady=10, padx=20, sticky="w")

# 경로를 선택 및 입력할 엔트리 위젯 및 버튼 생성
entry_image_folder_location = tk.Entry(window, width=50)
entry_image_folder_location.grid(row=1, column=1, columnspan=2, pady=10, padx=20, sticky="w")

btn_image_folder_location = tk.Button(window, text="파일 찾기", command=open_file_dialog)
btn_image_folder_location.grid(row=1, column=3, pady=10, padx=20, sticky="w")

# 체크 버튼 생성
check_button_imei = tk.Checkbutton(window, text="IMEI", variable=var_imei, onvalue="IMEI", offvalue="", command=on_check_button_change)
check_button_usim = tk.Checkbutton(window, text="USIM Number", variable=var_usim, onvalue="USIM Number", offvalue="", command=on_check_button_change)
check_button_line_number = tk.Checkbutton(window, text="회선번호", variable=var_line_number, onvalue="회선번호", offvalue="", command=on_check_button_change)
check_button_ip = tk.Checkbutton(window, text="IP", variable=var_ip, onvalue="IP", offvalue="", command=on_check_button_change)
check_button_system_title = tk.Checkbutton(window, text="SystemTitle", variable=var_system_title, onvalue="SystemTitle", offvalue="", command=on_check_button_change)
check_button_serial_number = tk.Checkbutton(window, text="Serial Number", variable=var_serial_number, onvalue="Serial Number", offvalue="", command=on_check_button_change)

# 체크 버튼을 그리드에 배치
check_button_imei.grid(row=2, column=1, pady=5, padx=20, sticky="w")
check_button_usim.grid(row=2, column=2, pady=5, padx=20, sticky="w")
check_button_line_number.grid(row=2, column=3, pady=5, padx=20, sticky="w")
check_button_ip.grid(row=3, column=1, pady=5, padx=20, sticky="w")
check_button_system_title.grid(row=3, column=2, pady=5, padx=20, sticky="w")
check_button_serial_number.grid(row=3, column=3, pady=5, padx=20, sticky="w")

# 저장할 Text 위치를 보여줄 라벨 생성
label_create_text_location = tk.Label(window, text="Text 파일 저장 위치:")
label_create_text_location.grid(row=4, column=0, pady=10, padx=20, sticky="w")

# 저장할 Text 위치를 선택 및 입력할 엔트리 위젯 및 버튼 생성
entry_create_text_location = tk.Entry(window, width=50)
entry_create_text_location.grid(row=4, column=1, columnspan=2, pady=10, padx=20, sticky="w")

btn_create_text_location = tk.Button(window, text="파일 생성 위치 선택", command=lambda: open_create_location(entry_create_text_location))
btn_create_text_location.grid(row=4, column=3, pady=10, padx=20, sticky="w")

# 저장할 Text 이름을 보여줄 라벨 생성
label_create_text_name = tk.Label(window, text="Text 파일 명:")
label_create_text_name.grid(row=5, column=0, pady=10, padx=20, sticky="w")

# 저장할 Text 이름을 입력할 엔트리 위젯 생성
entry_create_text_name = tk.Entry(window, width=20)
entry_create_text_name.grid(row=5, column=1, columnspan=2, pady=10, padx=20, sticky="w")

# 특별한 버전 출력 원할시 체크 버튼 생성
special = tk.StringVar()
check_button_special = tk.Checkbutton(window, text="special_ver", variable=special, onvalue="special_ver", offvalue="", command=on_check_button_special)
check_button_special.grid(row=5, column=2, pady=5, padx=20, sticky="w")

# 파일 생성 버튼 생성
btn_create_text_file = tk.Button(window, text="파일 생성", command=create_text_file)
btn_create_text_file.grid(row=5, column=3, pady=10, padx=20, sticky="w")

# 저장할 Image 위치를 보여줄 라벨 생성
label_create_image_location = tk.Label(window, text="Image 저장 위치:")
label_create_image_location.grid(row=6, column=0, pady=10, padx=20, sticky="w")

# 저장할 Image 위치를 선택 및 입력할 엔트리 위젯 및 버튼 생성
entry_create_image_location = tk.Entry(window, width=50, state=tk.DISABLED)
entry_create_image_location.grid(row=6, column=1, columnspan=2, pady=10, padx=20, sticky="w")

btn_create_image_location = tk.Button(window, text="이미지 생성 위치 선택", command=lambda: open_create_location(entry_create_image_location), state=tk.DISABLED)
btn_create_image_location.grid(row=6, column=3, pady=10, padx=20, sticky="w")

# 선택 결과를 표시할 레이블 생성 (텍스트 파일 생성 결과)
label_result = tk.Label(window, text="")
label_result.grid(row=7, column=0, columnspan=4, pady=20, padx=20, sticky="w")

# Tkinter 이벤트 루프 시작
window.mainloop()
