
# to calculate MTTC (Mean Turns To Conversion) for conversational effieciency requirements

class MeanTurnsToConversion:
    def calculate(
        self,
        conversion_turn: int | None,
    ) -> float:

        if conversion_turn is None:
            return 0.0

        return float(conversion_turn)

    def calculate_sessions(
        self,
        conversion_turns: list[int | None],
    ) -> float:

        successful_turns = [
            turn
            for turn in conversion_turns
            if turn is not None
        ]

        if not successful_turns:
            return 0.0

        return sum(successful_turns) / len(
            successful_turns
        )