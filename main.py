import sys
from PyQt5.QtWidgets import QWidget, QPushButton, QLabel, QApplication, QTableWidgetItem, QRadioButton, QComboBox, \
    QLineEdit, QFileDialog, QDialog, QDialogButtonBox, QVBoxLayout, QTableWidget
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt
from PyQt5.QtSql import QSqlDatabase, QSqlTableModel
import sqlite3
from itertools import product
import math
import random
from PIL import Image
import os


class CustomDialog(QDialog):
    def __init__(self):
        super().__init__()
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.No

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QVBoxLayout()
        message = QLabel("Удалить карту?")
        self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


class PerlinNoiseFactory:
    def __init__(self, dimension, octaves=1, tile=(), unbias=False):
        self.dimension = dimension
        self.octaves = octaves
        self.tile = tile + (0,) * dimension
        self.unbias = unbias
        self.scale_factor = 2 * dimension ** -0.5
        self.gradient = {}

    def smoothstep(self, t):
        return t * t * (3. - 2. * t)

    def lerp(self, t, a, b):
        return a + t * (b - a)

    def _generate_gradient(self):
        if self.dimension == 1:
            return random.uniform(-1, 1),
        random_point = [random.gauss(0, 1) for _ in range(self.dimension)]
        scale = sum(n * n for n in random_point) ** -0.5
        return tuple(coord * scale for coord in random_point)

    def get_plain_noise(self, *point):
        if len(point) != self.dimension:
            raise ValueError("Expected {} values, got {}".format(
                self.dimension, len(point)))
        grid_coords = []
        for coord in point:
            min_coord = math.floor(coord)
            max_coord = min_coord + 1
            grid_coords.append((min_coord, max_coord))
        dots = []
        for grid_point in product(*grid_coords):
            if grid_point not in self.gradient:
                self.gradient[grid_point] = self._generate_gradient()
            gradient = self.gradient[grid_point]

            dot = 0
            for i in range(self.dimension):
                dot += gradient[i] * (point[i] - grid_point[i])
            dots.append(dot)
        dim = self.dimension
        while len(dots) > 1:
            dim -= 1
            s = self.smoothstep(point[dim] - grid_coords[dim][0])
            next_dots = []
            while dots:
                next_dots.append(self.lerp(s, dots.pop(0), dots.pop(0)))
            dots = next_dots

        return dots[0] * self.scale_factor

    def __call__(self, *point):
        ret = 0
        for o in range(self.octaves):
            o2 = 1 << o
            new_point = []
            for i, coord in enumerate(point):
                coord *= o2
                if self.tile[i]:
                    coord %= self.tile[i] * o2
                new_point.append(coord)
            ret += self.get_plain_noise(*new_point) / o2
        ret /= 2 - 2 ** (1 - self.octaves)

        if self.unbias:
            r = (ret + 1) / 2
            for _ in range(int(self.octaves / 2 + 0.5)):
                r = self.smoothstep(r)
            ret = r * 2 - 1
        return ret


def generation(file):
    size = 10000
    res = 10
    frames = 10
    frameres = 10
    space_range = size // res
    frame_range = frames // frameres
    size = 100

    pnf = PerlinNoiseFactory(3, octaves=4, tile=(space_range, space_range, frame_range))
    img = Image.new("RGB", (size, size))
    for x in range(size * i, size * (i + 1)):
        for y in range(size * j, size * (j + 1)):
            n = int((pnf(x / res, y / res, frameres) + 1) * 7) - 4
            if n <= 0:
                img.putpixel((x % size, y % size), (50, 83, 173, 68))
            elif n == 1:
                img.putpixel((x % size, y % size), (72, 119, 247, 97))
            elif n == 2:
                img.putpixel((x % size, y % size), (237, 225, 52, 93))
            elif n == 3:
                img.putpixel((x % size, y % size), (81, 240, 54, 94))
            elif n == 4:
                img.putpixel((x % size, y % size), (60, 179, 30, 70))
            else:
                img.putpixel((x % size, y % size), (38, 112, 25, 44))
    img.save(file[:-4] + str(i) + str(j) + file[-4:])


class Play(QWidget):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.initUI()

    def initUI(self):
        self.setGeometry(300, 300, 400, 400)
        self.setWindowTitle("Путь")

        con = sqlite3.connect("map.db")
        cur = con.cursor()
        result = cur.execute(f"""select x, y from map0 where path = '{self.path}'""").fetchall()
        for i in result:
            r = i
        self.x, self.y = r
        con.commit()
        con.close()

        try:
            assert open(self.path)
        except FileNotFoundError:
            generation(self.path)

        self.im = QPixmap(self.path)
        self.im = self.im.copy(self.x, self.y, 10, 10)

        self.label = QLabel(self)
        self.label.move(50, 5)
        self.label.resize(300, 300)
        self.label.setScaledContents(True)
        self.label.setPixmap(self.im)

        self.text = QLabel("☻", self)
        self.text.move(180, 140)
        self.text.setFont(QFont("Times", 20))

        self.up = QPushButton("↑", self)
        self.up.move(180, 310)
        self.up.resize(40, 30)
        self.up.clicked.connect(self.upward)

        self.le = QPushButton("←", self)
        self.le.move(135, 340)
        self.le.resize(40, 30)
        self.le.clicked.connect(self.left)

        self.ri = QPushButton("→", self)
        self.ri.move(225, 340)
        self.ri.resize(40, 30)
        self.ri.clicked.connect(self.right)

        self.do = QPushButton("↓", self)
        self.do.move(180, 370)
        self.do.resize(40, 30)
        self.do.clicked.connect(self.down)

        self.exit = QPushButton("x", self)
        self.exit.move(360, 10)
        self.exit.resize(30, 30)
        self.exit.clicked.connect(self.getOverHere)

        self.back = QPushButton("<", self)
        self.back.move(10, 10)
        self.back.resize(30, 30)
        self.back.clicked.connect(self.saveMap)

    def getOverHere(self):
        dlg = CustomDialog()
        if dlg.exec():
            self.delMap()

    def saveMap(self):
        con = sqlite3.connect("map.db")
        cur = con.cursor()
        result = cur.execute(f"""UPDATE map0 SET x = {self.x}, y = {self.y}
                                    where path = '{self.path}'""").fetchall()
        con.commit()
        con.close()
        self.entry = Entry()
        self.entry.show()
        self.close()

    def delMap(self):
        con = sqlite3.connect("map.db")
        cur = con.cursor()
        result = cur.execute(f"""DELETE from user where mapId = (select id from map0 where
                                        path = '{self.path}')""").fetchall()
        con.commit()
        con.close()
        con = sqlite3.connect("map.db")
        cur = con.cursor()
        result = cur.execute(f"""DELETE from map0 where path = '{self.path}'""").fetchall()
        con.commit()
        con.close()
        os.remove(self.path)
        self.entry = Entry()
        self.entry.show()
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_W:
            self.upward()
        if event.key() == Qt.Key_A:
            self.left()
        if event.key() == Qt.Key_S:
            self.down()
        if event.key() == Qt.Key_D:
            self.right()

    def upward(self):
        if self.y != 0:
            self.y -= 1
            self.im = QPixmap(self.path)
            self.im = self.im.copy(self.x, self.y, 10, 10)
            self.label.setPixmap(self.im)

    def left(self):
        if self.x != 0:
            self.x -= 1
            self.im = QPixmap(self.path)
            self.im = self.im.copy(self.x, self.y, 10, 10)
            self.label.setPixmap(self.im)

    def right(self):
        if self.x != 86:
            self.x += 1
            self.im = QPixmap(self.path)
            self.im = self.im.copy(self.x, self.y, 10, 10)
            self.label.setPixmap(self.im)

    def down(self):
        if self.y != 86:
            self.y += 1
            self.im = QPixmap(self.path)
            self.im = self.im.copy(self.x, self.y, 10, 10)
            self.label.setPixmap(self.im)


class Admin(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setGeometry(300, 300, 541, 375)
        self.setWindowTitle("Путь Админа")

        self.db = QSqlDatabase.addDatabase("QSQLITE")
        self.db.setDatabaseName("map.db")
        self.db.open()

        self.model = QSqlTableModel(self, self.db)
        self.model.setTable("user")
        self.model.select()

        self.tableViewed = "user"
        self.modified = {}
        self.titles = None
        self.rows = []

        self.tableWidget = QTableWidget(self)
        self.update_result("user")
        self.tableWidget.move(10, 50)
        self.tableWidget.resize(521, 315)
        self.tableWidget.itemChanged.connect(self.item_changed)

        self.radioButtonUser = QRadioButton("user", self)
        self.radioButtonUser.setChecked(True)
        self.radioButtonUser.move(190, 15)
        self.radioButtonUser.toggled.connect(self.radioNow)

        self.radioButtonMap = QRadioButton("map0", self)
        self.radioButtonMap.move(280, 15)
        self.radioButtonMap.toggled.connect(self.radioNow)

        self.saveButton = QPushButton("save", self)
        self.saveButton.move(440, 5)
        self.saveButton.resize(91, 40)
        self.saveButton.clicked.connect(lambda _: self.save_results(self.tableViewed))

        self.back = QPushButton("<", self)
        self.back.move(5, 5)
        self.back.resize(40, 40)
        self.back.clicked.connect(self.getOverHere)

    def getOverHere(self):
        self.entry = Entry()
        self.entry.show()
        self.close()

    def update_result(self, table):
        try:
            self.con = sqlite3.connect("map.db")
            cur = self.con.cursor()
            result = cur.execute(f"SELECT * FROM '{table}'").fetchall()
            self.tableWidget.setRowCount(len(result))
            self.tableWidget.setColumnCount(len(result[0]))
            self.titles = [description[0] for description in cur.description]
            for i, elem in enumerate(result):
                for j, val in enumerate(elem):
                    self.tableWidget.setItem(i, j, QTableWidgetItem(str(val)))
            self.modified = {}
        except IndexError:
            pass

    def item_changed(self, item):
        if "id" not in self.titles[item.column()].lower():
            self.modified[self.titles[item.column()]] = item.text()
            self.rows += [item.row()]

    def save_results(self, table):
        if self.modified:
            con = sqlite3.connect("map.db")
            cur = con.cursor()
            result = cur.execute(f"""select id 
                                    from {table}""").fetchall()
            mass = list(map(lambda x: list(x)[0], list(result)))
            con.commit()
            con.close()
            for i in self.rows:
                cur = self.con.cursor()
                que = f"UPDATE {table} SET\n"
                que += ", ".join([f"{key}='{self.modified.get(key)}'"
                                  for key in self.modified.keys()])
                que += "WHERE id = " + str(mass[i])
                cur.execute(que)
                self.con.commit()
            self.modified.clear()

    def radioNow(self):
        self.save_results(self.tableViewed)
        self.tableViewed = self.sender().text()
        self.update_result(self.tableViewed)
        self.model.select()
        self.save_results(self.tableViewed)


class Registration(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setGeometry(300, 300, 400, 400)
        self.setWindowTitle("Путь")

        self.registrationLabel = QLabel("РЕГИСТРАЦИЯ", self)
        self.registrationLabel.move(37, 5)
        self.registrationLabel.setFont(QFont("Times", 25))

        self.nameLabel = QLabel("логин", self)
        self.nameLabel.move(180, 75)

        self.nameLineEdit = QLineEdit(self)
        self.nameLineEdit.move(5, 100)
        self.nameLineEdit.resize(390, 50)

        self.passwordLabel = QLabel("пароль", self)
        self.passwordLabel.move(180, 155)

        self.passwordLineEdit = QLineEdit(self)
        self.passwordLineEdit.move(5, 175)
        self.passwordLineEdit.resize(390, 50)

        self.password2Label = QLabel("подтвердите пароль", self)
        self.password2Label.move(150, 230)

        self.password2LineEdit = QLineEdit(self)
        self.password2LineEdit.move(5, 250)
        self.password2LineEdit.resize(390, 50)

        self.registrationLineEdit = QPushButton("регистрация", self)
        self.registrationLineEdit.move(25, 320)
        self.registrationLineEdit.resize(350, 50)
        self.registrationLineEdit.clicked.connect(self.ok)

        self.erorLabel = QLabel("                                                            ", self)
        self.erorLabel.move(105, 375)
        self.erorLabel.setFont(QFont("Times", 15))

        self.back = QPushButton(">", self)
        self.back.move(365, 5)
        self.back.resize(30, 30)
        self.back.clicked.connect(self.backEntry)

    def backEntry(self):
        self.entry = Entry()
        self.entry.show()
        self.close()

    def ok(self):
        if self.passwordLineEdit.text() == self.password2LineEdit.text():
            con = sqlite3.connect("map.db")
            cur = con.cursor()
            result = cur.execute(f"""select id from map0""").fetchall()
            r = 1
            for i in result:
                r = i
            con.commit()
            con.close()
            fname = QFileDialog.getSaveFileName(self, 'Выбрать картинку', f'image{r}'[:-2] + ")", 'Картинка (*.png)')[0]
            con = sqlite3.connect("map.db")
            cur = con.cursor()
            cur.execute(f"""INSERT INTO map0(path, x, y)
                            VALUES ('{fname}', 50, 50) """).fetchall()
            con.commit()
            con.close()
            con = sqlite3.connect("map.db")
            cur = con.cursor()
            cur.execute(f"""INSERT INTO user(name, password, mapId)
                            VALUES ('{self.nameLineEdit.text()}', '{self.passwordLineEdit.text()}', 
                            (select id from map0 where path = '{fname}')) """).fetchall()
            con.commit()
            con.close()
            generation(fname)
            self.backEntry()
        else:
            self.erorLabel.setText("пароли не совпадают")


class Entry(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setGeometry(300, 300, 400, 400)
        self.setWindowTitle("Путь")

        self.createAdminPassword()

        self.entryLabel = QLabel("ВХОД", self)
        self.entryLabel.move(140, 5)
        self.entryLabel.setFont(QFont("Times", 30))

        self.nameLabel = QLabel("логин", self)
        self.nameLabel.move(180, 75)

        self.nameComboBox = QComboBox(self)
        con = sqlite3.connect("map.db")
        cur = con.cursor()
        result = cur.execute("""select name from user""").fetchall()
        con.commit()
        con.close()
        for i in result:
            self.nameComboBox.addItem(str(*i))
        self.nameComboBox.move(5, 100)
        self.nameComboBox.resize(390, 50)

        self.passwordLabel = QLabel("пароль", self)
        self.passwordLabel.move(180, 155)

        self.passwordLineEdit = QLineEdit(self)
        self.passwordLineEdit.move(5, 175)
        self.passwordLineEdit.resize(390, 50)

        self.registrationPushButton = QPushButton("регистрация", self)
        self.registrationPushButton.move(5, 235)
        self.registrationPushButton.resize(190, 50)
        self.registrationPushButton.clicked.connect(self.registration)

        self.playPushButton = QPushButton("играть", self)
        self.playPushButton.move(205, 235)
        self.playPushButton.resize(190, 50)
        self.playPushButton.clicked.connect(self.play)

        self.erorLabel = QLabel("                                                            ", self)
        self.erorLabel.move(105, 325)
        self.erorLabel.setFont(QFont("Times", 15))

    def createAdminPassword(self):
        with open("password.txt", "w", encoding='utf8') as f:
            st1 = ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'p', 'a', 's', 'd', 'f', 'g',
                   'h', 'j', 'k', 'z', 'x', 'c', 'v', 'b', 'n', 'm']
            st2 = ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'P', 'A', 'S', 'D', 'F', 'G', 'H',
                   'J', 'K', 'L', 'Z', 'X', 'C', 'V', 'B', 'N', 'M']
            st3 = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
            st4 = st1 + st2 + st3
            pas = [random.choice(st1), random.choice(st2), random.choice(st3)]
            for i in range(16):
                pas.append(random.choice(st4))
            f.write("".join(pas))

    def play(self):
        with open("password.txt", "r", encoding='utf8') as f:
            if f.readline() == self.passwordLineEdit.text():
                self.shadow = Admin()
                self.shadow.show()
                self.close()
        try:
            con = sqlite3.connect("map.db")
            cur = con.cursor()
            result = cur.execute(f"""select password 
                from user where name = '{self.nameComboBox.currentText()}'""").fetchall()
            r = "",
            for i in result:
                r = i
            result = r
            result, = result
            con.commit()
            con.close()
            if str(result) == self.passwordLineEdit.text():
                con = sqlite3.connect("map.db")
                cur = con.cursor()
                result = cur.execute(f"""select path 
                    from map0 where id = (select mapId 
                    from user where name = '{self.nameComboBox.currentText()}')""").fetchall()[0]
                result, = result
                con.commit()
                con.close()
                self.pl = Play(result)
                self.pl.show()
                self.close()
            else:
                self.erorLabel.setText("неверный пароль")
        except sqlite3.OperationalError:
            self.erorLabel.setText("неверный пароль")

    def registration(self):
        self.regist = Registration()
        self.regist.show()
        self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    entry = Entry()
    entry.show()
    sys.exit(app.exec())
