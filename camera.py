import cv2

def scan_product():

    cap = cv2.VideoCapture(0)

    print("\n")
    print("Product IDs")
    print("1 Milk")
    print("2 Bread")
    print("3 Rice")
    print("4 Soap")
    print("5 Chocolate")
    print("\n")

    while True:

        ret, frame = cap.read()

        cv2.putText(
            frame,
            "Press S to Scan Product",
            (30,50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0,255,0),
            2
        )

        cv2.imshow(
            "TrolleyWise Camera",
            frame
        )

        key = cv2.waitKey(1)

        if key == ord('s'):

            pid = int(
                input(
                    "Enter Product ID: "
                )
            )

            cap.release()
            cv2.destroyAllWindows()

            return pid

        elif key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

    return None